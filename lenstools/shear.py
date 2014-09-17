"""

.. module:: shear 
	:platform: Unix
	:synopsis: This module implements a set of operations which are usually performed on weak lensing shear maps


.. moduleauthor:: Andrea Petri <apetri@phys.columbia.edu>


"""

from __future__ import division

from external import _topology
from convergence import ConvergenceMap

import numpy as np

#FFT engines
from numpy.fft import rfft2,irfft2,fftfreq

#Check if rfftfreq is implemented (requires numpy>=1.8)
try:
	from numpy.fft import rfftfreq
except ImportError:
	from utils import rfftfreq

#Units
from astropy.units import deg,rad

try:
	import matplotlib.pyplot as plt
	from matplotlib.colors import LogNorm
	matplotlib = True
except ImportError:
	matplotlib = False

##########################################
########ShearMap class####################
##########################################

class ShearMap(object):

	"""
	A class that handles 2D shear maps and allows to perform a set of operations on them

	>>> from lenstools import ShearMap
	
	>>> test = ShearMap.fromfilename("shear.fit",loader=lenstools.defaults.load_fits_default_shear)
	>>> test.side_angle
	1.95
	>>> test.gamma
	#The actual map values

	"""

	def __init__(self,gamma,angle):

		#Sanity check
		assert angle.unit.physical_type=="angle"

		self.gamma = gamma
		self.side_angle = angle

	@classmethod
	def fromfilename(cls,*args,**kwargs):
		
		"""
		This class method allows to read the map from a data file; the details of the loading are performed by the loader function. The only restriction to this function is that it must return a tuple (angle,gamma)

		:param args: The positional arguments that are to be passed to the loader (typically the file name)

		:param kwargs: Only one keyword is accepted "loader" is a pointer to the previously defined loader method (a template is defaults.load_fits_default_shear above)
		
		"""

		assert "loader" in kwargs.keys(),"You must specify a loader function!"
		loader = kwargs["loader"]

		angle,gamma = loader(*args)
		return cls(gamma,angle)

	@classmethod
	def fromEBmodes(cls,fourier_E,fourier_B,angle=3.14*deg):

		"""
		This class method allows to build a shear map specifying its E and B mode components

		:param fourier_E: E mode of the shear map in fourier space
		:type fourier_E: numpy 2D array, must be of type np.complex128 and must have a shape that is appropriate for a real fourier transform, i.e. (N,N/2 + 1); N should be a power of 2

		:param fourier_B: B mode of the shear map in fourier space
		:type fourier_B: numpy 2D array, must be of type np.complex128 and must have a shape that is appropriate for a real fourier transform, i.e. (N,N/2 + 1); N should be a power of 2

		:param angle: Side angle of the real space map in degrees
		:type angle: float.

		:returns: the corresponding ShearMap instance

		:raises: AssertionErrors for inappropriate inputs

		"""

		assert fourier_E.dtype == np.complex128 and fourier_B.dtype == np.complex128
		assert fourier_E.shape[1] == fourier_E.shape[0]/2 + 1
		assert fourier_B.shape[1] == fourier_B.shape[0]/2 + 1
		assert fourier_E.shape == fourier_B.shape

		#Compute frequencies
		lx = rfftfreq(fourier_E.shape[0])
		ly = fftfreq(fourier_E.shape[0])

		#Safety check
		assert len(lx)==fourier_E.shape[1]
		assert len(ly)==fourier_E.shape[0]

		#Compute sines and cosines of rotation angles
		l_squared = lx[np.newaxis,:]**2 + ly[:,np.newaxis]**2
		l_squared[0,0] = 1.0

		sin_2_phi = 2.0 * lx[np.newaxis,:] * ly[:,np.newaxis] / l_squared
		cos_2_phi = (lx[np.newaxis,:]**2 - ly[:,np.newaxis]**2) / l_squared

		sin_2_phi[0,0] = 0.0
		cos_2_phi[0,0] = 0.0

		#Invert E/B modes and find the components of the shear
		ft_gamma1 = cos_2_phi * fourier_E - sin_2_phi * fourier_B
		ft_gamma2 = sin_2_phi * fourier_E + cos_2_phi * fourier_B

		#Invert Fourier transforms
		gamma1 = irfft2(ft_gamma1)
		gamma2 = irfft2(ft_gamma2)

		#Instantiate new shear map class
		new = cls(np.array([gamma1,gamma2]),angle)
		setattr(new,"fourier_E",fourier_E)
		setattr(new,"fourier_B",fourier_B)

		return new

	
	def visualize(self,fig=None,ax=None,**kwargs):

		"""
		Visualize the shear map; the kwargs are passed to imshow 

		"""

		if not matplotlib:
			raise ImportError("matplotlib is not installed, cannot visualize!")

		#Instantiate figure
		if (fig is None) or (ax is None):
			
			self.fig,self.ax = plt.subplots(1,2,figsize=(16,8))

		else:

			self.fig = fig
			self.ax = ax

		#Plot the map
		self.ax[0].imshow(self.gamma[0],origin="lower",interpolation="nearest",extent=[0,self.side_angle.value,0,self.side_angle.value],**kwargs)
		self.ax[1].imshow(self.gamma[1],origin="lower",interpolation="nearest",extent=[0,self.side_angle.value,0,self.side_angle.value],**kwargs)

		#Axes labels
		self.ax[0].set_xlabel(r"$x$({0})".format(self.side_angle.unit.to_string()))
		self.ax[0].set_ylabel(r"$y$({0})".format(self.side_angle.unit.to_string()))
		self.ax[0].set_title(r"$\gamma_1$")
		self.ax[1].set_xlabel(r"$x$({0})".format(self.side_angle.unit.to_string()))
		self.ax[1].set_ylabel(r"$y$({0})".format(self.side_angle.unit.to_string()))
		self.ax[1].set_title(r"$\gamma_2$")

	
	def savefig(self,filename):

		"""
		Saves the map visualization to an external file

		:param filename: name of the file on which to save the map
		:type filename: str.

		"""

		self.fig.savefig(filename)


	def sticks(self,fig=None,ax=None,pixel_step=10,multiplier=1.0):

		"""
		Draw the ellipticity map using the shear components

		:param ax: ax on which to draw the ellipticity field
		:type ax: matplotlib ax object

		:param pixel_step: One arrow will be drawn every pixel_step pixels to avoid arrow overplotting
		:type pixel_step: int.

		:param multiplier: Multiplies the stick length by a factor
		:type multiplier: float.

		:returns: ax -- the matplotlib ax object on which the stick field was drawn

		>>> import matplotlib.pyplot as plt
		>>> test = ShearMap.fromfilename("shear.fit",loader=load_fits_default_shear)
		>>> fig,ax = plt.subplots()
		>>> test.sticks(ax,pixel_step=50)

		"""

		if not(matplotlib):
			raise ImportError("matplotlib is not installed, cannot visualize!")

		#Instantiate fig,ax objects
		if (fig is None) or (ax is None):
			self.fig,self.ax = plt.subplots()
		else:
			self.fig = fig
			self.ax = ax

		x,y = np.meshgrid(np.arange(0,self.gamma.shape[2],pixel_step),np.arange(0,self.gamma.shape[1],pixel_step))

		#Translate shear components into sines and cosines
		cos_2_phi = self.gamma[0] / np.sqrt(self.gamma[0]**2 + self.gamma[1]**2)
		sin_2_phi = self.gamma[1] / np.sqrt(self.gamma[0]**2 + self.gamma[1]**2)

		#Compute stick directions
		cos_phi = np.sqrt(0.5*(1.0 + cos_2_phi)) * np.sign(sin_2_phi)
		sin_phi = np.sqrt(0.5*(1.0 - cos_2_phi))

		#Fix ambiguity when sin_2_phi = 0
		cos_phi[sin_2_phi==0] = np.sqrt(0.5*(1.0 + cos_2_phi[sin_2_phi==0]))

		#Draw map using matplotlib quiver
		self.ax.quiver(x*self.side_angle.value/self.gamma.shape[2],y*self.side_angle.value/self.gamma.shape[1],cos_phi[x,y],sin_phi[x,y],headwidth=0,units="height",scale=x.shape[0]/multiplier)

		#Axes labels
		self.ax.set_xlabel(r"$x$({0})".format(self.side_angle.unit.to_string()))
		self.ax.set_ylabel(r"$y$({0})".format(self.side_angle.unit.to_string()))



	def decompose(self,l_edges,keep_fourier=False):

		"""
		Decomposes the shear map into its E and B modes components and returns the respective power spectral densities at the specified multipole moments

		:param l_edges: Multipole bin edges
		:type l_edges: array

		:param keep_fourier: If set to True, holds the Fourier transforms of the E and B mode maps into the E and B attributes of the ShearMap instance
		:type keep_fourier: bool. 

		:returns: :returns: tuple -- (l -- array,P_EE,P_BB,P_EB -- arrays) = (multipole moments, EE,BB power spectra and EB cross power)

		>>> test_map = ShearMap.fromfilename("shear.fit",loader=load_fits_default_shear)
		>>> l_edges = np.arange(300.0,5000.0,200.0)
		>>> l,EE,BB,EB = test_map.decompose(l_edges)

		"""

		#Perform Fourier transforms
		ft_gamma1 = rfft2(self.gamma[0])
		ft_gamma2 = rfft2(self.gamma[1])

		#Compute frequencies
		lx = rfftfreq(ft_gamma1.shape[0])
		ly = fftfreq(ft_gamma1.shape[0])

		#Safety check
		assert len(lx)==ft_gamma1.shape[1]
		assert len(ly)==ft_gamma1.shape[0]

		#Compute sines and cosines of rotation angles
		l_squared = lx[np.newaxis,:]**2 + ly[:,np.newaxis]**2
		l_squared[0,0] = 1.0

		sin_2_phi = 2.0 * lx[np.newaxis,:] * ly[:,np.newaxis] / l_squared
		cos_2_phi = (lx[np.newaxis,:]**2 - ly[:,np.newaxis]**2) / l_squared

		#Compute E and B components
		ft_E = cos_2_phi * ft_gamma1 + sin_2_phi * ft_gamma2
		ft_B = -1.0 * sin_2_phi * ft_gamma1 + cos_2_phi * ft_gamma2

		ft_E[0,0] = 0.0
		ft_B[0,0] = 0.0

		assert ft_E.shape == ft_B.shape
		assert ft_E.shape == ft_gamma1.shape

		#Compute and return power spectra
		l = 0.5*(l_edges[:-1] + l_edges[1:])
		P_EE = _topology.rfft2_azimuthal(ft_E,ft_E,self.side_angle.to(deg).value,l_edges)
		P_BB = _topology.rfft2_azimuthal(ft_B,ft_B,self.side_angle.to(deg).value,l_edges)
		P_EB = _topology.rfft2_azimuthal(ft_E,ft_B,self.side_angle.to(deg).value,l_edges)

		if keep_fourier:
			self.fourier_E = ft_E
			self.fourier_B = ft_B

		return l,P_EE,P_BB,P_EB


	def convergence(self):
		
		"""
		Reconstructs the convergence from the E component of the shear

		:returns: new ConvergenceMap instance 

		"""

		#Compute Fourier transforms if it wasn't done before
		if not hasattr(self,"fourier_E"):
			l_edges = np.array([200.0,400.0])
			l,EE,BB,EB = self.decompose(l_edges,keep_fourier=True)

		#Invert the Fourier transform to go back to real space
		conv = irfft2(self.fourier_E)

		#Return the ConvergenceMap instance
		return ConvergenceMap(conv,self.side_angle)

	def visualizeComponents(self,fig,ax,components="EE,BB,EB",region=(200,9000,-9000,9000)):

		"""
		Plots the full 2D E and B mode power spectrum (useful to test statistical isotropicity)

		:param fig: figure on which to draw the ellipticity field
		:type fig: matplotlibfigure object

		:param ax: ax on which to draw the ellipticity field
		:type ax: matplotlib ax object or array of ax objects, can be None in which case new ax are created

		:param components: string that contains the components to plot; the format is a sequence of {EE,BB,EB} separated by commas 
		:type components:

		:param region: selects the multipole region to visualize
		:type region: tuple (lx_min,lx_max,ly_min,ly_max)

		"""

		if not(matplotlib):
			raise ImportError("matplotlib is not installed, cannot visualize!")

		#Set value for frequency pixelization
		lpix = 360.0/self.side_angle.to(deg).value

		#First parse the components to plot from the components string
		component_list = components.split(",")
		if not len(component_list):
			return None

		for component in component_list:
			assert component=="EE" or component=="BB" or component=="EB", "Each of the components should be one of {EE,BB,EB}"

		#Check if the Fourier transforms are computed, if not compute them
		if not hasattr(self,"fourier_E"):
			l_edges = np.array([200.0,400.0])
			self.decompose(l_edges,keep_fourier=True)

		#Instantiate figure
		if (fig is None) or (ax is None):
			
			self.fig,self.ax = plt.subplots(1,len(components))

		else:

			assert len(component_list)==np.size(ax), "You should specify a plotting ax for each component!"
			self.fig = fig
			self.ax = ax


		#Do the plotting
		for n,component in enumerate(component_list):

			if len(component_list)==1:
				plot_ax = self.ax
			else:
				plot_ax = self.ax[n]

			#Select the numpy array of the appropriate component
			if component=="EE":
				mode = np.abs(self.fourier_E)**2 
			elif component=="BB":
				mode = np.abs(self.fourier_B)**2
			elif component=="EB":
				mode = np.abs((self.fourier_E * self.fourier_B.conjugate()).real)

			stacked = np.vstack((mode[self.fourier_E.shape[0]/2:],mode[:self.fourier_E.shape[0]/2])) * (self.side_angle.to(rad).value)**2/(self.fourier_E.shape[0]**4)
			assert stacked.shape == self.fourier_E.shape

			#Plot the components with the right frequencies on the axes
			plot_cbar = plot_ax.imshow(stacked,origin="lower",interpolation="nearest",norm=LogNorm(),extent=[0,lpix*stacked.shape[1],-lpix*stacked.shape[0]/2,lpix*stacked.shape[0]/2])
			plot_ax.set_xlim(region[0],region[1])
			plot_ax.set_ylim(region[2],region[3])

			#Set labels
			plot_ax.set_xlabel(r"$l_x$")
			plot_ax.set_ylabel(r"$l_y$")
			plot_ax.set_title(r"${0}$".format(component))

			#Set colorbar
			plt.colorbar(plot_cbar,ax=plot_ax)

			#Set tick size
			plot_ax.tick_params(labelsize='small')
			plot_ax.xaxis.get_major_formatter().set_powerlimits((0, 1))
			plot_ax.yaxis.get_major_formatter().set_powerlimits((0, 1))
			plot_ax.ticklabel_format(style='sci')
