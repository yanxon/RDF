from math import pi
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy.spatial.distance import cdist
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter1d

def smear(data, sigma):
    """
    
    Applying Gaussian smearing to spectrum
    
    Args:
        sigma: Std dev for Gaussian smear function
        
    """
    
    diff = [data[i + 1,0] - data [i,0] for i in range(len(data)-1)] #can I rewrite this in different form?
    avg_x_per_step = np.sum(diff) / len(diff)
    data[:,1] = gaussian_filter1d(data[:,1], sigma / avg_x_per_step)
    
    return data

class RDF(object):
    """
    a class of crystal structure.
    
    Args:
        crystal: crystal class from pymatgen
        symmetrize: symmetrize the structure before computing RDF
        R_max: maximum cutoff distance
        R_bin: length of each bin when computing the RDF
        width: width of Gaussian smearing
    
    Attributes:
        crystal
        R_max
        R_bin
        width
        RDF
        plot_RDF()
    """
    
    def __init__(self, crystal, symmetrize=True, R_max=12, R_bin=0.2, sigma=0.2):
        """Return a RDF object with the proper info"""
        self.R_max = R_max
        self.R_bin = R_bin
        self.sigma = sigma
        self.crystal = crystal
        if symmetrize:
            finder = SpacegroupAnalyzer(crystal, symprec=0.06, angle_tolerance=5)
            crystal = finder.get_conventional_standard_structure()
            
        self.compute_RDF(crystal)
        
    def RDF_in_box(self, crystal, R_max, R_bin):
        """ PDF for the box """
        R = np.zeros(round(R_max/R_bin))
            
        rij_dot = np.dot(crystal.frac_coords, crystal.latttice.matrix)
        for atom in crystal.frac_coords:
            origin = [np.dot(atom, crystal.lattice.matrix)]
            rij_dist = cdist(rij_dot, origin)
            for i in range(len(R)):
                d_min, d_max = R_bin * (i+0.5), R_bin * (i+1.5)
                R[i] += len([x for x in rij_dist if d_min <= x < d_max])
                
        return R/2
    
    def find_supercell(self, crystal, R_max, atom = [0.5, 0.5, 0.5]):
        #make supercell to cover big sphere centered at atom with a radius of R_max
        #for all basic directions (1,0,0), (0,1,0), (1,1,0), (1,-1,0), etc. 26 in total
        hkl_max = np.array([1,1,1])
        for h1 in [-1,0,1]:
            for k1 in [-1,0,1]:
                for l1 in [-1,0,1]:
                    hkl_index = np.array([[h1,k1,l1]])
                    R = float(np.linalg.norm(np.dot(hkl_index-atom, crystal.lattice.matrix), axis = 1))
                    multiple = round(R_max/R)
                    hkl_index *= multiple
                    for i in range(len(hkl_max)):
                        if hkl_max[i] < hkl_index[0,i]:
                            hkl_max[i] = hkl_index[0,i]
                            
        h, k, l = hkl_max
        coors = []
        for a in range (-h,h+1):
            for b in range (-k,k+1):
                for c in range (-l,l+1):
                    for coor in crystal.frac_coords:
                        coors.append(coor+[a,b,c])
                        
        supercell = np.asarray(coors)
        rij_dot = np.dot(supercell, crystal.lattice.matrix)
        
        return rij_dot
        
    def compute_RDF(self, crystal):
        R_max = self.R_max
        R_bin = self.R_bin
        
        R = np.zeros(round(R_max/R_bin))
        #R1 = self.RDF_in_box(crystal, R_max, R_bin)
        rij_dot = self.find_supercell(crystal, R_max)
        
        for atom in crystal.frac_coords:
            origin = [np.dot(atom, crystal.lattice.matrix)]
            rij_dist = cdist(rij_dot, origin)
            for i in range (len(R)):
                d_min, d_max = R_bin * (i+0.5), R_bin * (i+1.5)
                R[i] += len([x for x in rij_dist if d_min <= x < d_max])
                
        self.RDF = np.ones([len(R),2])
        rho = len(crystal.frac_coords)/crystal.volume
        for i in range(len(R)):
            r = (i+1)*R_bin
            self.RDF[i,0] = r
            self.RDF[i,1] = R[i]/(4*pi*R_bin*rho*r**2)/len(crystal.frac_coords)
            
    def plot_RDF(self, filename = None):
        datax = smear(self.RDF, self.sigma)
        plt.plot(datax[:,0], datax[:,1])
        #ax = plt.gca()
        plt.grid()
        plt.xlabel(r"$r (\AA)$", fontsize = 16)
        plt.ylabel(r"$g(r)$", fontsize = 16)
        if filename is None:
            plt.show()
        else:
            plt.savefig(filename)
            plt.close()
            
from optparse import OptionParser
#import pandas as pd
#from tabulate import tabulate

if __name__ == "__main__": #if this file is directly running by Python; then do the following:
    #-------------------------------- Options -------------------------
    parser = OptionParser()
    parser.add_option("-c", "--crystal", dest="structure",default='',
                      help="crystal from file, cif or poscar, REQUIRED", metavar="crystal")
    parser.add_option("-r", "--Rmax", dest="Rmax", default=12, type='float',
                      help="Rmax, default: 12 A", metavar="Rmax")
    parser.add_option("-s", "--sigma", dest="sigma",default=0.20, type='float',
            help="sigma width for Gaussian smearing, default: 0.20", metavar="sigma")
    parser.add_option("-d", "--delta", dest="delta",default=0.08, type='float',
            help="step length, default: 0.08", metavar="R_bin")
    parser.add_option("-o", "--output", dest="mstyle",default='bmh',
            help="matplotlib style, fivethirtyeight, bmh, grayscale, dark_background, ggplot", metavar="mstyle")

    (options, args) = parser.parse_args()    
    if options.structure.find('cif') > 0:
       fileformat = 'cif'
    else:
       fileformat = 'poscar'