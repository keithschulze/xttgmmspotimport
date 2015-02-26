#
#
#  Python TGMM Spot Importer XTension
#
#  Copyright (c) 2015 Keith Schulze (keith.schulze@monash.edu), BSD-style copyright and disclaimer apply
#
#    <CustomTools>
#      <Menu>
#       <Item name="Import TGMM Spots" icon="Python" tooltip="Imports TGMM output files (Amat et al., Nature Methods, 2014).">
#         <Command>PythonXT::XTTGMMSpotImport(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>

import os
import time
import threading
import Queue
import numpy as np
from numpy import linalg as la
from numpy.lib import recfunctions
from lxml import etree
from pIceImarisConnector import pIceImarisConnector as ice

# GUI Imports
import Tkinter
import ttk
import tkFileDialog
import tkMessageBox


class TGMMImportUI:
    def __init__(self, master, conn, queue):
        self.queue = queue
        self.labeltext = Tkinter.StringVar()
        self.labeltext.set("TGMM Import")
        label = Tkinter.Label(master, width=50, textvariable=self.labeltext)
        self.prog = ttk.Progressbar(master, orient='horizontal', length=300,
                                   mode='determinate')
        label.pack(padx=10, pady=10)
        self.prog.pack(padx=10, pady=10)

    def processincoming(self):
        while self.queue.qsize():
            try:
                msg = self.queue.get(0)
                self.labeltext.set(msg)
                self.prog.step(15)
            except Queue.Empty:
                pass


class TGMMImporter:

    def __init__(self, master, conn):
        self.master = master
        self.conn = conn
        self.queue = Queue.Queue()
        self.gui = TGMMImportUI(master, conn, self.queue)
        self.running = True

        options = {'mustexist': True,
                   'parent': master,
                   'title': 'Please select TGMM output folder'}
        self.folder_path = tkFileDialog.askdirectory(**options)
        if len(self.folder_path) == 0:
            self.master.quit()
            raise Exception("Open folder cancelled")

        threading.Thread(target=self.workerthread).start()
        self.periodiccall()

    def periodiccall(self):
        self.gui.processincoming()
        if self.running:
            self.master.after(10, self.periodiccall)

    def workerthread(self):

        if not os.path.exists(self.folder_path):
            print "Folder path does not exist"
            tkMessageBox.showwarning(
                "nonexistent folder",
                "Folder does not exist!"
            )
            time.sleep(2)
            self.master.quit()
            raise Exception("Folder not found.")

        self.queue.put("Getting dataset dimensions")
        x, y, z, c, t = self.conn.getSizes()
        vX, vY, vZ = self.conn.getVoxelSizes()
        xmin, xmax, ymin, ymax, zmin, zmax = self.conn.getExtends()

        self.queue.put("Getting TGMM file list")
        file_list = filter(self.accept, os.listdir(self.folder_path))
        file_list = [os.path.join(self.folder_path, f) for f in file_list]
        if len(file_list) != t:
            print "Number of timepoints does not match current dataset"
            tkMessageBox.showwarning(
                "frame number mismatch",
                "Number of timepoints does not match current dataset!"
            )
            time.sleep(2)
            self.master.quit()
            raise Exception("Frame number mismatch")

        self.queue.put("Reading and parsing TGMM output")
        data = self.read_tgmm_output(file_list)

        self.queue.put("Reshape data")
        centroid_matrix = np.multiply(data[['x', 'y', 'z']].view("<f8").reshape((len(data), 3)),
                                      np.array([vX, vY, -vZ]))
        centroid_matrix = np.subtract(centroid_matrix, [0, 0, zmin])
        frames = data['frame']
        radii = np.multiply(data['spotr'], np.average(np.array([vX, vY, vZ])))
        edges = filter(self.edge_filter, data[['parent', 'id']])
        edges = np.array(edges).view("<i8").reshape((len(edges), 2))

        # Add spot score as statistics
        score_value = data['score']
        score_name = ["Score"] * len(score_value)
        score_unit = [""] * len(score_value)
        score_cat = ["Spot"] * len(score_value)
        score_ch = [""] * len(score_value)
        score_col = [""] * len(score_value)
        score_time = data['frame'] * self.conn.mImarisApplication.GetDataSet().GetTimePointsDelta()
        score_factors = np.array([score_cat, score_ch, score_col, score_time])
        score_fns = ["Category", "Channel", "Collection", "Time"]
        score_ids = np.arange(len(score_value))

        self.queue.put("Creating spots")

        spots_name = "TGMM Spots "
        existing_tgmm_spots = 0
        existing_spots = self.conn.getAllSurpassChildren(True, typeFilter="Spots")
        for es in existing_spots:
            if spots_name in es.GetName():
                existing_tgmm_spots += 1

        spots = self.conn.mImarisApplication.GetFactory().CreateSpots()
        spots.Set(centroid_matrix.tolist(), frames.tolist(), radii.tolist())
        spots.SetName(spots_name + str(existing_tgmm_spots))
        spots.SetTrackEdges(edges.tolist())

        spots.AddStatistics(score_name, score_value.tolist(), score_unit,
                        score_factors.tolist(), score_fns, score_ids.tolist())
        self.conn.mImarisApplication.GetSurpassScene().AddChild(spots, -1)
        self.running = False
        self.master.quit()

    def getcentroid(self, centstr):
        centroid = centstr.strip().split(" ")
        return centroid[0], centroid[1], centroid[2]


    def getscale(self, scalestr):
        scale = scalestr.strip().split(" ")
        return scale[0], scale[1], scale[2]


    def getprecisionmatrix(self, pms):
        pm = np.asmatrix(np.array(pms.strip().split(" "), dtype=np.float32).reshape((3, 3)))
        return pm


    def estimatespotradius(self, precisemat, nu):
        if np.isnan(precisemat).any() or np.isinf(precisemat).any():
            return np.nan
        covmat = la.inv(precisemat*nu)
        sigmas = 2
        radii, v = la.eig(covmat)
        radii = np.sqrt(radii)
        radius = sigmas * np.average(radii)
        return radius


    def getedges(self, _id, parent):
        if parent != '-1':
            return [parent, _id]


    def getallattributes(self, el, frame):
        _id = int(el.attrib['id'])
        lineage = el.attrib['lineage']
        parent = int(el.attrib['parent'])
        score = el.attrib['splitScore']
        nu = float(el.attrib['nu'])
        spotr = self.estimatespotradius(self.getprecisionmatrix(el.attrib['W']), nu)
        x, y, z = self.getcentroid(el.attrib['m'])
        xscale, yscale, zscale = self.getscale(el.attrib['scale'])

        return (_id, lineage, parent, score, frame, spotr, x, y, z,
                xscale, yscale, zscale)


    def process_tgmm_xml(self, file_path, frame):
        if not os.path.exists(file_path):
            print "File does not exist"
            return

        xml = etree.parse(file_path)
        xml_root = xml.getroot()

        spot_attribs = np.array([self.getallattributes(e, frame) for e in xml_root.getchildren()],
                                dtype=[('id', int), ('lineage', int), ('parent', int),
                                       ('score', int), ('frame', int), ('spotr', float),
                                       ('x', float), ('y', float), ('z', float),
                                       ('xscale', float), ('yscale', float), ('zscale', float)])

        return spot_attribs


    def accept(self, file_path):
        return file_path.endswith(".xml")


    def add_parent_offset(self, parent, offset):
        if parent != -1:
            return parent + offset
        else:
            return parent


    def read_tgmm_output(self, file_list):
        offset = 0
        prev_offset = 0
        outputs = []
        for i, f in enumerate(file_list):
            attribs = self.process_tgmm_xml(f, i)
            attribs['id'] += offset
            attribs['parent'] = [self.add_parent_offset(p, prev_offset) for p in attribs['parent']]
            prev_offset = offset
            offset += attribs.shape[0]
            outputs.append(attribs)

        return recfunctions.stack_arrays(outputs, usemask=False)


    def edge_filter(self, p):
        return p[0] != -1


def XTTGMMSpotImport(aImarisId):

    # Get a connection
    conn = ice(aImarisId)

    # Check if the object is valid
    if not conn.isAlive():
        print 'Could not connect to Imaris!'
        tkMessageBox.showwarning(
            "connection failed",
            "Could not connect to Imaris!"
        )
        time.sleep(2)
        return

    root = Tkinter.Tk()
    client = TGMMImporter(root, conn)
    root.mainloop()
