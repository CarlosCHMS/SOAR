# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 10:39:23 2017

@author: carlos
"""

import numpy
import matplotlib.pyplot as plt
from scipy.integrate import ode

# Global variables
GM = 398600.4415       # km^3 s^-2
R = 6371               # km
pi = numpy.pi

def main ():

	h_final = 463.0     # km
	Mu = 90.0        # Payload mass [kg]		

	fator_V = 1.06    # Ajust to find a final V
	tf = 480.0        # Ajust to find a final gamma
	tAoA = 0.5        #Ajust to find a final h

	fsup = numpy.array([1.1,500.0,2])
	finf = numpy.array([0.9,400.0,0.1])

	factors = numpy.array([fator_V,tf,tAoA])

	# Results without automatic adjustment
	tt0,xx0,uu0,tp0,xp0,up0 = trajectoryDesing(factors,h_final,Mu,"plot")
	h,v,gama,M = numpy.transpose(xx0[-1,:])
	orbitResults(h,v,gama)
	plotResults(tt0,xx0,uu0,tp0,xp0,up0)
	

	# Aplication of the simplitied bisection method
	df = (fsup - finf)/100
	factors1 = factors
	factors2 = factors + df
	errors1, tt, xx = trajectoryDesing(factors1,h_final,Mu,"design") # inicialization
	continuing = True
	count = 0.0
	Nmax = 20
	while continuing and (count < Nmax):
				
		errors2, tt, xx = trajectoryDesing(factors2,h_final,Mu,"design")
		factors3 = factors1 - errors1*(factors2 - factors1)/(errors2 - errors1)
		
		# boundary verification		
		onInterval(factors3,finf,fsup)
		
		# error calculation
		errors3, tt, xx = trajectoryDesing(factors3,h_final,Mu,"design")		
		verify = abs(errors3) < 1.0
		
		if verify[0] and verify[1] and verify[2]:
			continuing = False			
			
		else:
			errors1 = errors2
			errors2 = errors3
			factors1 = factors2
			factors2 = factors3			
			count += 1
			print("\n\rBisection iteration: ",count)
	
	print("\n\rFinal factors: ",factors3)		
	print("\n\rFinal errors: ",errors3,"\n\r")
	h,v,gama,M = numpy.transpose(xx)
	orbitResults(h,v,gama)	
		
	# Results with automatic adjustment
	tt0,xx0,uu0,tp0,xp0,up0 = trajectoryDesing(factors3,h_final,Mu,"plot")
	h,v,gama,M = numpy.transpose(xx0[-1,:])
	orbitResults(h,v,gama)
	plotResults(tt0,xx0,uu0,tp0,xp0,up0)
	
	# Results with automatic adjustment
	tt0,xx0,uu0,tp0,xp0,up0 = trajectoryDesing(factors3,h_final,Mu,"orbital")
	h,v,gama,M = numpy.transpose(xx0[-1,:])
	orbitResults(h,v,gama)
	plotResults(tt0,xx0,uu0,tp0,xp0,up0)

	return None
	
def trajectoryDesing(factors,h_final,Mu,typeResult):	

	# example rocket single stage to orbit L=0 D=0
	# initial state condition
	h_initial = 0.0            # km
	V_initial = 1.0e-6         # km/s
	gamma_initial = 90*pi/180  # rad
	# Initial mass definied in bellow	
	
	# final state condition
	V_final = numpy.sqrt(GM/(R+h_final))   # km/s Circular velocity
	gamma_final = 0.0 # rad
		
	Isp = 450              # s
	efes = .95
	g0 = 9.8e-3            # [km s^-2] gravity acceleration on earth surface
	AoAmax = 2.0           # graus

	##########################################################################
     # Trajetory design parameters
	fator_V,tf,tAoA = factors
	fdv1 = 1.4 #Ajust to find a final h

	##########################################################################
	# Initial mass definition and thrust programm
	Dv1 = fdv1*numpy.sqrt(2.0*GM*(1/R - 1/(R+h_final)))
	Dv2 = V_final

	Dv2 = Dv2*fator_V
	LamMax = 1/(1-efes)
	Lam1 = numpy.exp(Dv1/g0/Isp)
	Lam2 = numpy.exp(Dv2/g0/Isp)
	
	Mp2 = (Lam2-1)*efes*Mu/(1 - Lam2*(1-efes))
	Mp1 = (Lam1-1)*efes*(Mu + (Mp2/efes))/(1 - Lam1*(1-efes))
	Mp = Mp1 + Mp2;
	Me = (1-efes)*Mp/efes
	M0 = Mu + Mp + Me

	T = 40.0e3 # thrust in N
	T *= 1.0e-3 # thrust in kg * km / s^2 [for compatibility purposes...]

	tb1 = Mp1 * g0 * Isp / T
	tb2 = Mp2 * g0 * Isp / T

	# thrust program
	#tabBeta = retPulse(tb1,(tf-tb2),1.0,0.0)
	tVec = numpy.array([tb1,(tf-tb2),tf,tf*1.1])
	vVec = numpy.array([1.0,0.0,1.0,0.0])
	tabBeta = retPulse2(tVec,vVec)

	##########################################################################
	# Attitude program definition
	# Chossing tAoA1 as a fraction of tf results in code bad behavior
	# So a fixed generic number is used
	tAoA1 = 4.4 # [s], maneuver initiates 4.4 seconds from lift off
	tAoA2 = tAoA1 + tAoA

	# Attitude program
	#tabAlpha = retPulse(tAoA1,tAoA2,0.0,-AoAmax*pi/180)
	tVec = numpy.array([tAoA1,tAoA2,tf])
	vVec = numpy.array([0.0,-AoAmax*pi/180,0.0])
	tabAlpha = retPulse2(tVec,vVec)

	

	##########################################################################
	#Integration

	# initial conditions
	t0 = 0.0
	x0 = numpy.array([h_initial,V_initial,gamma_initial,M0])

     # Integrator setting
     # ode set:
     #         atol: absolute tolerance
     #         rtol: relative tolerance
	ode45 = ode(mdlDer).set_integrator('dopri5',nsteps=1,atol = 1.0e-9,rtol = 1.0e-10)
	ode45.set_initial_value(x0, t0).set_f_params((tabAlpha,tabBeta,T,Isp,g0,R))

	# Phase times, incluiding the initial time in the begining
	
	if (typeResult == "orbital"):
	
		tphases = numpy.array([t0,tAoA1,tAoA2,tb1,(tf-tb2),tf,2*pi*(R + h_final)/V_final])
		
	else:
		
		tphases = numpy.array([t0,tAoA1,tAoA2,tb1,(tf-tb2),tf])
	
	
	if (typeResult == "design"):
		# Integration using rk45 separated by phases
		# Trajetory design parameters
		# fator_V,tf,tAoA = factors
		# Automatic multiphase integration
		tt,xx,tp,xp = totalIntegration(tphases,ode45,False)
		h,v,gamma,M = xx
		errors = ((v - V_final)/0.001, (gamma - gamma_final)/0.001, (h - h_final)/1.0)
		errors = numpy.array(errors)
		return errors, tt, xx
		
	elif (typeResult == "plot") or (typeResult == "orbital"):		
		# Integration using rk45 separated by phases
		# Automatic multiphase integration
		print("\n\rDv =",Dv1,"Dv =",Dv2," Lam1 =",Lam1," Lam2 =",Lam2,"LamMax =",LamMax)
		print("\n\rMu =",Mu," Mp =",Mp," Me =",Me,"M0 =",M0,"\n\r")
		tt,xx,tp,xp = totalIntegration(tphases,ode45,True)
		uu = numpy.concatenate([tabAlpha.multValue(tt),tabBeta.multValue(tt)], axis=1)
		up = numpy.concatenate([tabAlpha.multValue(tp),tabBeta.multValue(tp)], axis=1)
		ans = (tt,xx,uu,tp,xp,up)	
		return ans
		
	else:
		
		return None

def totalIntegration(tphases,ode45,flagAppend):

	def phaseIntegration(t_initial,t_final,Nref,ode45,tt,xx,tp,xp,flagAppend):
	
		tph = t_final - t_initial
		ode45.first_step = tph/Nref     
		stop1 = False
		while not stop1:
			ode45.integrate(t_final)
			if flagAppend:
				tt.append(ode45.t)
				xx.append(ode45.y)
			if ode45.t >= t_final:
				stop1 = True
		if flagAppend:
			tp.append(ode45.t)
			xp.append(ode45.y)
		else:
			tt = ode45.t
			xx = ode45.y
			
		return tt,xx,tp,xp

	Nref = 5.0 # Number of interval divisions for determine first step 	
	# Output variables
	tt,xx,tp,xp = [],[],[],[]

	for ii in range(1,len(tphases)):
		tt,xx,tp,xp = phaseIntegration(tphases[ii - 1],tphases[ii],Nref,ode45,tt,xx,tp,xp,flagAppend)
		if flagAppend:
			print("Phase integration iteration:",ii)

	tt = numpy.array(tt)
	xx = numpy.array(xx)
	tp = numpy.array(tp)
	xp = numpy.array(xp) 		
		
	return tt,xx,tp,xp

def onInterval(f,fmin,fmax):
	
	for ii in range(0,len(f)):
		if (f[ii] < fmin[ii]):
			f[ii] = fmin[ii]
		elif (f[ii] > fmax[ii]):
			f[ii] = fmax[ii]
	
	return f

def plotResults(tt,xx,uu,tp,xp,up):

	ii = 0
	plt.subplot2grid((6,4),(0,0),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,xx[:,ii],'.-b')
	plt.plot(tp,xp[:,ii],'.r')
	plt.hold(False)
	plt.grid(True)
	plt.ylabel("h [km]")
	
	ii = 1
	plt.subplot2grid((6,4),(0,2),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,xx[:,ii],'.-b')
	plt.plot(tp,xp[:,ii],'.r')
	plt.hold(False)
	plt.grid(True)
	plt.ylabel("V [km/s]")
	
	ii = 2
	plt.subplot2grid((6,4),(2,0),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,xx[:,ii]*180.0/numpy.pi,'.-b')
	plt.plot(tp,xp[:,ii]*180.0/numpy.pi,'.r')
	plt.hold(False)
	plt.grid(True)
	plt.ylabel("gamma [deg]")
	
	ii = 3
	plt.subplot2grid((6,4),(2,2),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,xx[:,ii],'.-b')
	plt.plot(tp,xp[:,ii],'.r')
	plt.hold(False)
	plt.grid(True)
	plt.ylabel("m [kg]")
	
	ii = 0
	plt.subplot2grid((6,4),(4,0),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,uu[:,ii],'.-b')
	plt.plot(tp,up[:,ii],'.r')
	plt.hold(False)
	plt.grid(True)
	plt.ylabel("alfa [rad]")
	
	ii = 1
	plt.subplot2grid((6,4),(4,2),rowspan=2,colspan=2)
	plt.hold(True)
	plt.plot(tt,uu[:,ii],'.-b')
	plt.plot(tp,up[:,ii],'.r')
	plt.hold(False)
	plt.grid(True)
	plt.xlabel("t")
	plt.ylabel("beta [adim]")
	
	#plt.subplots_adjust(0.0125,0.0,0.9,2.5,0.2,0.2)
	plt.show()				
				
	return None

def orbitResults(h,v,gama):

	r = R + h
	cosGama = numpy.cos(gama)
	sinGama = numpy.sin(gama)
	momAng = r * v * cosGama
	print("Ang mom:",momAng)
	en = .5 * v * v - GM/r
	print("Energy:",en)
	a = - .5*GM/en
	print("Semi-major axis:",a)
	aux = v * momAng / GM
	e = numpy.sqrt((aux * cosGama - 1)**2 + (aux * sinGama)**2)
	print("Eccentricity:",e)

	print("Final altitude:",h)
	ph = a * (1.0 - e) - R
	print("Perigee altitude:",ph)
	
	return None

def plotRockTraj(t,x,R,tb,tb2):

	pi = numpy.pi
	cos = numpy.cos
	sin = numpy.sin

	N = len(t)
	print("N =",N)
	dt = t[1]-t[0]
	X = numpy.empty(numpy.shape(t))
	Z = numpy.empty(numpy.shape(t))

	sigma = 0.0
	X[0] = 0.0
	Z[0] = 0.0
	for i in range(1,N):
		v = x[i,1]
		gama = x[i,2]
		dsigma = v * cos(gama) / (R+x[i,0])
		sigma += dsigma*dt

		X[i] = X[i-1] + dt * v * cos(gama-sigma)
		Z[i] = Z[i-1] + dt * v * sin(gama-sigma)



	print("sigma =",sigma)
	# get burnout point
	itb = int(tb/dt) - 1
	itb2 = int(tb2/dt) - 1
	h,v,gama,M = x[itb,:]
	print("itb =",itb)
	print("State @burnout time:")
	print("h = {:.4E}".format(h)+", v = {:.4E}".format(v)+\
	", gama = {:.4E}".format(gama)+", m = {:.4E}".format(M))


	plt.plot(X,Z)
	plt.grid(True)
	plt.hold(True)
	# Draw burnout point
	#plt.plot(X[:itb],Z[:itb],'r')
	#plt.plot(X[itb],Z[itb],'or')

#	plt.plot([0.0,0.0],[-1.0,0.0],'k')
#	plt.plot([0.0,sin(sigma)],[-1.0,-1.0+cos(sigma)],'k')
	s = numpy.arange(0,1.01,.01)*sigma
	x = R * cos(.5*pi - s)
	z = R * (sin(.5*pi - s) - 1.0)
	#z = -1 + numpy.sqrt(1-x**2)
	plt.plot(x,z,'k')
	plt.plot(X[:itb],Z[:itb],'r')
	plt.plot(X[itb],Z[itb],'or')
	plt.plot(X[itb2:],Z[itb2:],'g')
	plt.plot(X[itb2],Z[itb2],'og')
	plt.plot(X[1]-1,Z[1],'ok')
	plt.xlabel("X [km]")
	plt.ylabel("Z [km]")

	plt.axis('equal')
	plt.title("Rocket trajectory on Earth")
	plt.show()

	return None
	
def mdlDer(t,x,arg):
       
	h,v,gama,M = x[0],x[1],x[2],x[3]
	alfaProg,betaProg,T,Isp,g0,R = arg 
	betat = betaProg.value(t)
	alfat = alfaProg.value(t)
    
	btm = betat*T/M
	sinGama = numpy.sin(gama)
	g = g0*(R/(R+h))**2

	return numpy.array([v*sinGama,\
	btm*numpy.cos(alfat) - g*sinGama,\
	btm*numpy.sin(alfat)/v + (v/(h+R)-g/v)*numpy.cos(gama),\
	-btm*M/g0/Isp])	
	
def interpV(t,tVec,xVec):
	
	Nsize = xVec.shape[1]

	ans = numpy.empty(Nsize)
	for k in range(Nsize):
		ans[k] = numpy.interp(t,tVec,xVec[:,k])
	return ans
	
class retPulse():
	
	def __init__(self,t1,t2,v1,v2):
		self.t1 = t1
		self.t2 = t2
		self.v1 = v1
		self.v2 = v2
		
	def value(self,t):
		if (t < self.t1):
			return self.v1
		elif (t < self.t2):
			return self.v2
		else:
			return self.v1
			
	def multValue(self,t):
		N = len(t)
		ans = numpy.full((N,1),self.v1)
		for ii in range(0,N):
			if (t[ii] >= self.t1) and (t[ii] < self.t2):
				ans[ii] = self.v2
		return ans
		
class retPulse2():
	
	def __init__(self,tVec,vVec):
		self.tVec = tVec		
		self.vVec = vVec
		
	def value(self,t):
		ii = 0
		stop = False
		while not stop:
			if (t >= self.tVec[-1]):
				ans = self.vVec[-1]
				stop = True
			elif (t < self.tVec[ii]):
				ans = self.vVec[ii]
				stop = True
			else:
				ii = ii + 1
				
		return ans
							
	def multValue(self,t):
		N = len(t)
		ans = numpy.full((N,1),self.vVec[0])
		for jj in range(0,N):
			ans[jj] = self.value(t[jj])

		return ans			

main()