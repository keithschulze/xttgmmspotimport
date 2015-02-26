# TGMM Importer for Imaris
Imaris XTension for importing spots and tracks from [TGMM](http://tgmm.sourceforge.net/) tracking data into Imaris.

## Requirements
* Imaris and XT Module
* Python 2.*
* numpy
* lxml
* [pIceImarisConnector](http://www.scs2.net/next/index.php?id=110)

## Installation
You will need Python. On Windows I recommend installing the [Anaconda](http://continuum.io/downloads) distribution as it makes it easier to get all the dependencies. For nix systems, you can generally use the distributed version of Python or install it using the your systems package manager. On OS X, I recommend [Homebrew](http://brew.sh).

If you are willing, I also highly recommend getting familiar with virtual environments for Python, whether that be [virtualenv](https://virtualenv.pypa.io/) or the Anaconda flavour. I personally prefer to set up a virtualenv with all the dependencies that I need for analysis and iPython and then use that virtual env python executable in Imaris (see below).

### Install numpy and lxml
```
pip install -U numpy lxml
```

### Install pIceImarisConnector
You will need to install the [pIceImarisConnector](http://www.scs2.net/next/index.php?id=110) into your python environment. You can use the install instructions on the website or use the following:

```
git clone https://github.com/aarpon/pIceImarisConnector.git
cd pIceImarisConnector
pip install .
```
Note: If you are using a virtualenv with your Imaris XT, you will need to activate the environment first before running the pip install.

## Configure Imaris XT module
You will need to configure the XT module in Imaris to point to your Python executable:

1. Edit --> Preferences --> Custom Tools
2. Point to 'Python application' field to your Python installation. Important: If you installed a virtualenv, you need to point Imaris to that.

## Installing the iPython connect XTension
There are several ways one could do this, the aim is to get XTTGMMSpotImport.py file into a place where Imaris can find it. Perhaps the easiest way would be to clone this repo:
```
cd ~/path/to/personal/imaris/xtensions
git clone https://github.com/keithschulze/xttgmmspotimport.git
```
or to download the tar from github and put in somewhere where you would like to keep Imaris XTensions.

Then add that path into the 'XTension folders' box in the XT modules 'Custom Tools' config (see above).
