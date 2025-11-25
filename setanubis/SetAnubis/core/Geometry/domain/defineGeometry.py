import sys, os
import numpy as np
import matplotlib
#matplotlib.use('Qt5Agg')
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ion()
from sympy import Point3D, Line3D, Plane
import json
import pickle

#=========================================================#
# NOTE: The ATLAS Coordinate system is assumed throughout #
#=========================================================#
#   A side of ATLAS = +ve z
#   C side of ATLAS = -ve z
#   proANUBIS is on side A.

class ATLASCavern():
    # Define the parameters for the ATLAS cavern using technical drawings:
    #   - LHCJUX150002: Axial View (xy) of the ATLAS Cavern
    #   - ATFIU___0004: Side View (zy) of the ATLAS Cavern with the Access Shafts

    def __init__(self):
        #===========================================================================================================================#
        #===========================================================================================================================#
        # NOTE: All coordinates, measurements and functions are assumed to be relative to the cavern centre coordinate system
        #       If you use a different origin, e.g. in simulations, the positions must be converted before using these functions
        #===========================================================================================================================#
        #===========================================================================================================================#
        # Define a default origin for given (x,y,z) points, relative to the centre of the Cavern
        #   If instead you want to treat hits as coming from the IP, posOrigin = [IP["x"], IP["y"], IP["z"]]
        #   Then for each (x,y,z) point, before using the associated functions use coordsToOrigin(x,y,z, posOrigin)
        self.posOrigin = [0,0,0] 

        #=========================#
        #   Cavern Dimensions     #
        #=========================#
        # NOTE: On the ground floor of the cavern the length is exactly 30m, 
        #       however above 25.6m from the floor the cavern walls are thinner.
        #       Since ANUBIS Will be above this level, we take this larger size for our X Length
        self.CavernXLength = 31.0 #metres
        self.CavernX = [-self.CavernXLength/2, self.CavernXLength/2]

        # NOTE: Y here does not include the vaulted ceiling - this will be included separately.
        # Taken from Axial View of the Cavern.
        self.CavernYLength = 27.5 #metres
        self.CavernY = [-self.CavernYLength/2, self.CavernYLength/2]
        
        self.CavernZLength = 52.8 #metres  #Potentially 53m
        self.CavernZ = [-self.CavernZLength/2, self.CavernZLength/2]

        #=========================#
        #   Cavern Boundaries     #
        #=========================#
        self.CavernBounds = {"x": self.CavernX, "y": self.CavernY, "z": self.CavernZ}
        self.CavernCorners = {"X0Y0Z0": [self.CavernX[0],self.CavernY[0],self.CavernZ[0]],
                              "X0Y0Z1": [self.CavernX[0],self.CavernY[0],self.CavernZ[1]],
                              "X0Y1Z0": [self.CavernX[0],self.CavernY[1],self.CavernZ[0]],
                              "X0Y1Z1": [self.CavernX[0],self.CavernY[1],self.CavernZ[1]],
                              "X1Y0Z0": [self.CavernX[1],self.CavernY[0],self.CavernZ[0]],
                              "X1Y0Z1": [self.CavernX[1],self.CavernY[0],self.CavernZ[1]],
                              "X1Y1Z0": [self.CavernX[1],self.CavernY[1],self.CavernZ[0]],
                              "X1Y1Z1": [self.CavernX[1],self.CavernY[1],self.CavernZ[1]],
        }

        #=============================================================================#
        # The Interaction point does not align with the centre of the ATLAS Cavern.
        # Give the relative position to the centre of the ATLAS Cavern:
        self.IP = {"x": -1.7, #metres
                   "y": -self.CavernYLength/2 + 11.37, #metres #From https://core.ac.uk/download/pdf/44194071.pdf Page 14
                   "z": 0} #metres
        #=============================================================================#

        #===========================#
        #   Cavern Ceiling Arch     #
        #===========================#
        # The profile of the ATLAS Ceiling has been measured in: https://edms.cern.ch/document/2149688
        #   Gives the Equation of the cylinder to be: 20^2 = (x-1.7)^2 + (y-3.52)^2 relative to the IP
        #   Centre of Curvature of the ceiling doesn't align with the centre of the cavern 
        self.archRadius = 20 #metres, radius of curvature of the ceiling
        self.arcLength = self.archRadius * ( 2 * np.arcsin(self.CavernXLength / (2*self.archRadius)) )
        self.centreOfCurvature = {"x": 0, #metres, relative to cavern centre
                                  "y": self.IP["y"] + 3.52} #metres
        
        # Difference between the theoretical y level based on CavernYLength and that given by the ceiling profile relative to Cavern Centre 
        self.archOffset = self.CavernYLength/2 - np.sqrt(np.power(self.archRadius,2) - np.power(self.CavernX[0],2)) - self.centreOfCurvature["y"]
        
        #===========================#
        #  Service Shaft Parameters #
        #===========================#
        self.PX14_Centre = {"x": 0, #metres - aligns with cavern axis from edms 2149688
                            "y": self.centreOfCurvature["y"] + self.archRadius, #metres
                            "z": 13.5} #metres - From Axial View and edms 2149688

        self.PX14_Radius = 18/2 # metres
        self.PX14_Height = 57.85 # metres 
        self.PX14_LowestY = np.sqrt(np.power(self.archRadius,2) - (np.power(self.PX14_Radius - self.PX14_Centre["x"],2))) + self.centreOfCurvature["y"]

        self.PX16_Centre = {"x": 0, #metres - aligns with cavern axis from edms 2149688
                            "y": self.centreOfCurvature["y"] + self.archRadius, #metres
                            "z": -17.7} #metres - From Axial View and edms 2149688

        self.PX16_Radius = 12.6/2 # metres
        self.PX16_Height = 57.85 # metres
        self.PX16_LowestY = np.sqrt(np.power(self.archRadius,2) - (np.power(self.PX16_Radius - self.PX16_Centre["x"],2))) + self.centreOfCurvature["y"]

        self.shaftParams = {"PX14": {"Centre": self.PX14_Centre, "radius": self.PX14_Radius, "height": self.PX14_Height, "LowestY": self.PX14_LowestY},
                            "PX16": {"Centre": self.PX16_Centre, "radius": self.PX16_Radius, "height": self.PX16_Height, "LowestY": self.PX16_LowestY},
        }

        self.angles = self.calculateAngles()

        #===========================#
        # ATLAS Experimental Bounds #
        #===========================#
        self.radiusATLAS = 12 # metres, ATLAS experiment envelope (Estimated from Fig 1.3 from https://cds.cern.ch/record/2285580 (Oleg had 10.5m)
        #self.radiusATLAStracking = 7 # metres, ATLAS effective vertexing radius
        self.radiusATLAStracking = 9.5 # metres, ANUBIS volume limit accounting for the material veto of 30cm.
        self.ATLAS_ZLength = 44 # metres, ATLAS experiment envelope (Estimated from Fig 1.3 from https://cds.cern.ch/record/2285580 
        self.ATLAS_Z = [-self.ATLAS_ZLength/2 - self.IP["z"], self.ATLAS_ZLength/2 - self.IP["z"]] #ATLAS Z min and max in metres relative to Cavern centre
        self.ATLAS_Centre = self.IP # ATLAS Centre coincides with the IP

        self.ANUBIS_RPCs = []
        self.RPCeff = 1
        self.nRPCsPerLayer = 1 

    #------------------------------#
    #     Helper Functions         #
    #------------------------------#
    # Convert cartesian coordinates in terms of the Cavern Centre to be in terms of the IP instead
    #   - Useful as simulations are relative to the IP
    def cavernCentreToIP(self, x, y, z):
        return (x + self.IP["x"], y + self.IP["y"], z + self.IP["z"])

    # Convert cartesian coordinates in terms of the IP to be in terms of the Cavern Centre instead
    def IPTocavernCentre(self, x, y, z):
        return (x - self.IP["x"], y - self.IP["y"], z - self.IP["z"])

    # Generically convert position cartesian coordinates to the default origin and back
    def coordsToOrigin(self, x, y, z, origin=[]):
        if len(origin)==0:
            origin = self.posOrigin # Use the default position origin
        return (x - origin[0], y - origin[1], z - origin[2]) 

    # Undos the cartesian shift to new origin. 
    def reverseCoordsToOrigin(self, x, y, z, origin=[]):
        if len(origin)==0:
            origin = self.posOrigin # Use the default position origin
        return (x + origin[0], y + origin[1], z + origin[2]) 

    # Convert cartestian coordinates to cylindrical coordinates, where the circular face is in xy
    def cartToCyl(self, x, y, z):
        r = np.sqrt(x**2 + y**2)
        theta = np.arctan2(y, x)
        return (r, theta, z)

    # Convert cylindrical coordinates to cartestian coordinates, where the circular face is in xy
    def cylToCart(self, r, theta, z):
        return (r*np.cos(theta), r*np.sin(theta), z)

    # Convert spherical coordinates to cartestian coordinates
    def cartToSph(self, x, y, z):
        r = np.sqrt( (x**2) + (y**2) + (z**2) )
        theta = np.arccos(np.clip((z / r), -1.0, 1.0))
        phi = np.arctan2(y, x)
        if np.isclose(phi, np.pi):
            phi = -np.pi

        return (r, theta, phi)

    def sphToCart(self, r, theta, phi):
        x = r*np.sin(theta)*np.cos(phi)
        y = r*np.sin(theta)*np.sin(phi)
        z = r*np.cos(theta)
        return (x,y,z)

    def onCeiling(self, x, y, z, origin=[]):
        ceiling = np.power(x-self.centreOfCurvature["x"],2) + np.power(y-self.centreOFCurvature["y"],2)
        if (abs(self.archRadius - ceiling) < 0.01) and  (z > self.CavernZ[0] and z < self.CavernZ[1]):
            return (True, ceiling)
        else:
            return (False, ceiling)

    # Get the y coordinate of the cavern boundaries for a given x coordinate
    def obtainCavernYFromX(self, x): # Relative to Cavern Centre
        return self.centreOfCurvature["y"] + np.sqrt(self.archRadius**2 - np.power( (x-self.centreOfCurvature["x"]),2))

    # Get the x coordinate of the cavern boundaries for a given y coordinate
    def obtainCavernXFromY(self, y): # Relative to Cavern Centre
        return self.centreOfCurvature["x"] + np.sqrt(self.archRadius**2 - np.power( (y-self.centreOfCurvature["y"]),2))

    # Each point is a 3D position list
    def createVector(self, point1, point2):
        diff = np.array(point1) - np.array(point2)
        return diff / np.linalg.norm(diff)

    #============================================================#
    # Function to Determine if a point lies in the ATLAS Cavern  #
    #============================================================#
    def inCavern(self, x, y, z, maxRadius="", radiusOrigin=[],verbose=False): # x, y, z coordinates are relative to the Centre of the Cavern
        # Radius is assumed to be from the given origin (centre of curvature unless otherwise stated)
        if len(radiusOrigin)==0:
            radiusOrigin = (self.centreOfCurvature["x"], self.centreOfCurvature["y"], 0)

        # Max radius is given to optionally restrict "Cavern Area" to within a smaller radius of the centre of curvature
        # In particular since the ANUBIS vertexing limit is ~50cm below the closest tracking station to the IP.
        if maxRadius=="":
            radialAcceptance=True # No radius considered
        else:
            # Radial distance in cylindrical coordinates relative to the given origin
            r = np.linalg.norm( (x - radiusOrigin[0], y - radiusOrigin[1]) )
            radialAcceptance = r < maxRadius

        if verbose:
            print(f"Hit: ({x},{y},{z})")
            print(f"Radius Origin: {radiusOrigin}")
            print(f"RadialAcceptance: {radialAcceptance}")
            print(f"In X [{self.CavernX[0]},{self.CavernX[1]}: {(x > self.CavernX[0] and x < self.CavernX[1])}")
            print(f"In Y [{self.CavernY[0]},{self.CavernY[1]}: {(y > self.CavernY[0] and y < self.CavernY[1])}")
            print(f"In Z [{self.CavernZ[0]},{self.CavernZ[1]}: {(z > self.CavernZ[0] and z < self.CavernZ[1])}")

        #Assume x, y, z provided relative to the Cavern Centre
        if ((x > self.CavernX[0] and x < self.CavernX[1]) and #Within X Dimensions
            (y > self.CavernY[0] and y < self.obtainCavernYFromX(x)) and #Within Y Dimensions
            (z > self.CavernZ[0] and z < self.CavernZ[1]) and #Within Z Dimensions
            (radialAcceptance ) # Within a Radius if specified
            ):
            return True
        else:
            return False

    def inShaft(self, x, y, z, shafts=["PX14"], includeCavernCone=True):
        #Assume x, y, z provided relative to the Cavern Centre
        inShaft=[]
        for shaft in shafts:
            withinY = (y < self.shaftParams[shaft]["Centre"]["y"] + self.shaftParams[shaft]["height"]) or (y > self.shaftParams[shaft]["Centre"]["y"])
            withinXZ = np.sqrt(np.power(x - self.shaftParams[shaft]["Centre"]["x"],2) + 
                               np.power(z - self.shaftParams[shaft]["Centre"]["z"],2)) < self.shaftParams[shaft]["radius"]
            
            if includeCavernCone and (y < self.shaftParams[shaft]["Centre"]["y"]):
                coneTip = np.array([self.IP["x"], self.IP["y"], self.IP["z"]]) # Take the IP as the cone's tip
                point = np.array([x,y,z])
                
                xSign = np.sign(self.shaftParams[shaft]["Centre"]["x"])
                if xSign==0:
                    xSign=1
                zSign = np.sign(self.shaftParams[shaft]["Centre"]["z"])
                if zSign==0:
                    zSign=1
                x1 = self.shaftParams[shaft]["Centre"]["x"] - xSign*(self.shaftParams[shaft]["radius"])# + self.IP["x"])
                x2 = self.shaftParams[shaft]["Centre"]["x"] + xSign*(self.shaftParams[shaft]["radius"])# - self.IP["x"])
                z1 = self.shaftParams[shaft]["Centre"]["z"] - zSign*(self.shaftParams[shaft]["radius"])# + self.IP["z"])
                z2 = self.shaftParams[shaft]["Centre"]["z"] + zSign*(self.shaftParams[shaft]["radius"])# - self.IP["z"])
                l1 = np.sqrt( np.power(z1,2) + np.power(self.shaftParams[shaft]["Centre"]["y"],2)) 
                l2 = np.sqrt( np.power(z2,2) + np.power(self.shaftParams[shaft]["Centre"]["y"],2)) 
                coneOpeningAngle = np.arccos(np.clip(z1/l1,-1.0,1.0)) - np.arccos(np.clip(z2/l2,-1.0,1.0))

                coneBaseR = l2*np.sin(coneOpeningAngle/2) # The base Radius of the cone
                coneHeight = l2*np.cos(coneOpeningAngle/2) # The total height of the cone from base to tip

                baseCentre = np.array([ coneHeight*np.cos(coneOpeningAngle/2 + np.arccos(np.clip(x2/l2,-1.0,1.0))),
                                        coneHeight*np.sin(coneOpeningAngle/2 + np.arccos(np.clip(z2/l2,-1.0,1.0))),
                                        coneHeight*np.cos(coneOpeningAngle/2 + np.arccos(np.clip(z2/l2,-1.0,1.0)))])

                #direction vector of the cone
                divV=baseCentre - coneTip
                divV/=np.linalg.norm(divV)
                
                pointH = np.dot(divV, point - coneTip) # Project point along the cone axis -- gives height from tip.

                pointMaxR = (coneBaseR / coneHeight) * pointH # Using similar triangles get the radius of the circular section for pointH
                
                # Find the points radial distance from the cone axis
                pointR = np.sqrt( np.power(np.linalg.norm(point-coneTip),2) - np.power(pointH,2))

                # Check point is within the correct radial distance of the cone AND below the bottom of the shaft
                withinCone = (pointR < pointMaxR) and (y < self.shaftParams[shaft]["Centre"]["y"]) 

                #print(f"ConeTip: {coneTip} | baseCentre: {baseCentre} | coneOpeningAngle: {coneOpeningAngle}")
                #print(f"ConeBaseR: {coneBaseR} | ConeHeight: {coneHeight} | divV: {divV}")
                #print(f"pointH: {pointH} | pointMaxR: {pointMaxR} | pointR {pointR}")
                #print(f"withinCone: {withinCone}")

                return withinCone

            return withinY * withinXZ

    def inATLAS(self, x, y, z, trackingOnly=False, verbose=False): 
        #Assume x, y, z provided relative to the Cavern Centre
        # Radial distance in cylindrical coordinates relative to the cavern centre
        #   - ATLAS is defined as a cylinder with a defined radius here.
        r = np.linalg.norm( (x - self.IP["x"], y - self.IP["y"]) )

        if trackingOnly:
            rTarget = self.radiusATLAStracking #Effective vertexing radius
        else:
            rTarget = self.radiusATLAS # Entire ATLAS Envelope

        if verbose:
            print(f"r: {r} | rTarget: {rTarget} | {r<rTarget}")
            print(f"z: {z} | Z in ({self.ATLAS_Z[0]},{self.ATLAS_Z[1]}) | {(z > self.ATLAS_Z[0] and z < self.ATLAS_Z[1])}") 

        if ( (r < rTarget) and (z > self.ATLAS_Z[0] and z < self.ATLAS_Z[1]) ):
            return True
        else:
            return False

    def intersectANUBISstations(self, x, y, z, ANUBISstations, origin=[], verbose=False):
        # (x,y,z) is the position of a particle
        # ANUBISstations is a dictionary of RPCs, with a list of: 
        #   - "corners": The (x,y,z) positions of its 8 corners,
        #   - "midPoint": The (x,y,z) position of the midpoint,
        #   - "plane": A sympy Plane Object which goes through the midpoint
        #   - "LayerID" and "RPCid": which combine to form a unique ID to identify it
        # Origin allows the origin of the particle (x,y,z) to be set to determine its direction. If empty, assumed to originate from IP
        
        # Assume (x,y,z) and the origin position are provided relative to the cavern centre
        if len(origin)==0:
            origin = (self.IP["x"], self.IP["y"], self.IP["z"])

        coordSphere = self.cartToSph(x, y, z)
        
        direction = Line3D(Point3D(origin), Point3D((x,y,z)))

        nIntersections=0
        intersections=[]
        for i in range(len(ANUBISstations["plane"])):
            # Reduce function calls by only checking cases where the hit is within an angular separation of 0.1 of the RPC midpoint
            midSphere = self.cartToSph(ANUBISstations["midPoint"][i][0], ANUBISstations["midPoint"][i][1], ANUBISstations["midPoint"][i][2])
            if np.sqrt((midSphere[1]-coordSphere[1])**2 + (midSphere[2]-coordSphere[2])**2) > 0.1:
                continue

            tempIntersections = ANUBISstations["plane"][i].intersection(direction)

            if len(tempIntersections)!=0:
                #nIntersections+=len(tempIntersections) # Increment the number of intersections
                for intersect in tempIntersections:
                    if ((ANUBISstations["corners"][i][0][0] > intersect[0] and intersect[0] <  ANUBISstations["corners"][i][0][0]) and
                        (ANUBISstations["corners"][i][4][1] > intersect[1] and intersect[1] <  ANUBISstations["corners"][i][1][0]) and
                        (ANUBISstations["corners"][i][1][2] > intersect[2] and intersect[2] <  ANUBISstations["corners"][i][2][0])
                        ):
                        intersections.append((intersect[0], intersect[1], intersect[2])) # Store the Intersection points
                        nIntersections+=1

        return nIntersections, intersections

    def intersectANUBISstationsSimple(self, theta, phi, ANUBISstations, position=[], extremaPosition=[], verbose=False):
        # Theta and Phi are the angular direction of the particle
        # position: Position of the particle. If empty, assumed to be at the IP
        # ANUBISstations is a dictionary of a list of RPC layers represented by cylindrical shells, containing:
        #   - "r": List of [minRadius, maxRadius] (Representing the thickness of an RPC layer) relative to the centre of curvature.
        #   - "theta": List of [minTheta, maxTheta] (Representing the start and end of the chambers in angular coverage. Relative to IP
        #   - "phi": List of [minPhi, maxPhi]. Relative to IP
        #   extremaPosition: gives the extrema (x,y,z) to constrain the projection of the intersection 
        #       i.e. For non-final state tracks that travel from production vertex (position) to decay vertex (extremaPosition)
        
        # Assume the position coords are provided relative to the cavern centre
        if len(position)==0: 
            position = (self.IP["x"], self.IP["y"], self.IP["z"])

        if len(position)!=3:
            raise Exception(f"Invalid position provided, it should have 3 elements representing (x,y,z). Got: {position}")

        # ANUBIS stations are cylindrical shells relative to the centre of curvature (CoC)
        #   - determine the distance of the particle relative to the CoC
        particleR = np.linalg.norm( (position[0] - self.centreOfCurvature["x"], position[1] - self.centreOfCurvature["y"]))

        if verbose:
            print(f"Position (X,Y,Z): ({position}), Direction (theta,phi): ({theta},{phi}), Distance from CoC, R: {particleR}")
        
        #---------------------------------------------------------------------------------------------------------------------------
        # To determine whether the particle direction intersects with the cylindrical shells solve two separate equations:
        #   1. Intersection of y=m(x-c) + d (particle x-y direction) and the circular face of the cylinder (x-a)^2 + (y-b)^2 = r^2
        #      - Here (a,b) is the xy position of the CoC and (c,d) is the xy position of the particle, m = tan(phi) and 
        #        r is the radius of the cylinder. 
        #      - Setting (x-a)^2 + ( (m(x-c) + d) - b)^2 = r^2 obtain the expression: 
        #           (m^2+1)x^2 + 2(m(d-b -mc) -a)x + (a^2+b^2+m^2c^2+d^2-r^2 - 2mc((b+d)-bd) = 0  -> A*x^2 + B*x + C = 0 
        #           Solved with the quadratic equation, and check that x is within the correct range of the ANUBIS station
        #      - If particle is travelling vertically (i.e. phi=±pi) then set x=c (if it is in range) and then:
        #           y = b ± sqrt( r^2 - (c-a)^2)
        #   2. Intersection of y=n(z-e) + d and y=g (where g is the y value determined by the previous calculation)
        #       - This gives: z = (g-d)/n + e
        #---------------------------------------------------------------------------------------------------------------------------
        
        #For ease define terms as above:
        a, b = self.centreOfCurvature["x"], self.centreOfCurvature["y"]
        c, d, e = position
        m = np.tan(phi)
        n = np.tan(theta) if phi > 0 else np.tan(-theta) # Correctly determine if particle is up- or down-going

        nIntersections=0
        intersections=[]
        intersectionStations=[]
        for i in range(len(ANUBISstations["r"])):
            if verbose:
                print(f"Station {i}: (r,theta,phi): ({ANUBISstations['r'][i]},{ANUBISstations['theta']['IP'][i]},{ANUBISstations['phi']['IP'][i]})")
                print(f"\t r Requirement {particleR} > {ANUBISstations['r'][i][1]}: {particleR > ANUBISstations['r'][i][1]}")

            stationR = max(ANUBISstations["r"][i])

            if particleR > stationR: # ANUBIS r limits are in cylindrical coordinates relative to the Centre of Curvature
                if verbose:
                    print(f"Skipping Station...")
                continue

            # Intersection In xy:
            if np.isclose(phi,np.pi/2) or np.isclose(phi, (3/2)*np.pi):
                if verbose:
                    print("Treating trajectory as vertical...")
                # Vertical lines are simpler
                intX = c
                tY = [b + np.sqrt(stationR*stationR - np.power( (c-a),2)), b - np.sqrt(stationR*stationR - np.power( (c-a),2))]
                intIndex = np.argwhere(np.array(tY)>0)[0]
                
                if len(intIndex)==0:
                    continue

                intY = tY[intIndex[0]]

                if verbose:
                    print(f"IntX, IntY: {intX}, {intY}")

            else:
                A = np.power(m,2)+1
                B = 2*(m*(d - b - (m*c)) - a)
                C = (a*a + b*b + m*m*c*c + d*d - stationR*stationR - 2*(m*c*(d-b)  + b*d))

                discriminant = np.power(B,2) - 4*A*C
                
                if verbose:
                    print(f"\t XY discriminant: {discriminant} -> Intersections: {discriminant>0}")

                if discriminant <= 0: #No Intersections, ==0 is a tangent which is not valid for ANUBIS tracks
                    continue
                else:
                    tX = [(-B + np.sqrt(discriminant))/(2*A), (-B - np.sqrt(discriminant))/(2*A)]
                    tY = [m*(tX[0]-c)+d, m*(tX[1]-c)+d]

                    intIndex = np.argwhere(np.array(tY)>0)
                    if verbose:
                        print(f"Full intersection solutions (x,y): {tX} | {tY}")
                        print(intIndex, len(intIndex), intIndex[0], len(intIndex[0]))
                    
                    if len(intIndex)==0:
                        continue
                    
                    elif len(intIndex)==1: 
                        # For a chord that passes through a +ve and -ve solution, where the -ve solution has been discarded
                        intX = tX[intIndex[0][0]]
                        intY = tY[intIndex[0][0]]
                    else:
                        # For a chord that passes through two +ve solutions, and the one in the direction of the particle should be selected
                        phiDiff=[]
                        for tempIntX, tempIntY in zip(tX, tY):
                            vec1 = self.createVector([tempIntX, tempIntY], [position[0], position[1]])
                            vec2 = self.createVector([self.CavernX[1], 0], [0, 0])
                            tempPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                            tempPhi = np.sign(vec1[1])*np.arccos(np.clip(tempPhi, -1, 1)) # In radians
                            print(f"vec1 vec2: {vec1}, {vec2}")
                            print(f"phi, tempPhi: {phi}, {tempPhi} | {abs(phi-tempPhi)}")

                            phiDiff.append(abs(phi - tempPhi))

                        # Pick the one in the direction of the particle i.e. that has the minimum phi distance:
                        minPhiIndex= phiDiff.index(min(phiDiff)) 
                        intX = tX[minPhiIndex]
                        intY = tY[minPhiIndex]

                        if verbose: 
                            print(f"Disambiguating two positive solutions, difference in phi angle: {phiDiff}, take index of minimum {minPhiIndex}")

                    if verbose:
                        print(f"IntX, IntY: {intX}, {intY}")

            # Intersection in zy
            intZ = np.sqrt(np.power((intY - d),2)+np.power((intX-c),2))/n + e
            if verbose:
                print(f"d, n, e: {d}, {n}, {e}")
                print(f"IntZ: {intZ}")

            # Check if intersections are valid
            # - i.e. if they're within the circular section defined by the ANUBIS stations and within the cavern bounds.
            extremaX = []
            for tempPhi in ANUBISstations['phi']['CoC'][i]:
                extremaX.append(stationR * np.cos(tempPhi) + self.centreOfCurvature["x"])

            if verbose:
                print(f"\t Valid X range:  {intX} in {min(extremaX)} to {max(extremaX)}? {not(intX < min(extremaX) or intX > max(extremaX))}")
                print(f"\t Cavern X range: {intX} in {min(self.CavernX)} to {max(self.CavernX)}?", 
                                         f"{not(intX<min(self.CavernX) or intX > max(self.CavernX))}")
            if (intX < min(extremaX) or intX > max(extremaX)) or (intX<min(self.CavernX) or intX > max(self.CavernX)):
                continue

            extremaZ = []
            for i in [1,0]:
                # Getting minimum Y values to get max theta coverage: This is on the X boundaries of the cavern.
                vec1 = self.createVector([self.CavernZ[i], intY], [0, 0])
                vec2 = self.createVector([self.CavernZ[1], 0], [0, 0])
                tempTheta = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                tempTheta = np.arccos(np.clip(tempTheta, -1, 1)) # In radians

                if np.isclose(tempTheta, np.pi/2) or np.isclose(tempTheta, -np.pi/2):
                    extremaZ.append(self.IP["z"])
                else:
                    extremaZ.append(intY/np.tan(tempTheta) + self.IP["z"])
                    
            if verbose:
                print(f"\t Valid Z range: {intZ} in {min(extremaZ)} to {max(extremaZ)}? {not(intZ < min(extremaZ) or intZ > max(extremaZ))}")
                print(f"\t Cavern Z range: {intZ} in {min(self.CavernZ)} to {max(self.CavernZ)}?",
                                         f"{not(intZ < min(self.CavernZ) or intZ > max(self.CavernZ))}")
            if (intZ < min(extremaZ) or intZ > max(extremaZ)) or (intZ<min(self.CavernZ) or intZ > max(self.CavernZ)):
                continue
            
            # Check that projected intersection point does not exceed the extremaPosition if given
            if len(extremaPosition)!=0:
                constrainedR = np.linalg.norm([extremaPosition[i]-position[i] for i in [0,1,2]]) 
                intersectionR = np.linalg.norm([intX-position[0], intY-position[1], intZ-position[2]])

                if verbose:
                    print(f"ConR, IntR: {constrainedR}, {intersectionR} | intR > constrainedR {intersectionR > constrainedR}")

                if intersectionR > constrainedR:
                    continue

            # Sanity Check that the intersection point is in the correct direction
            sanityThreshold = 1E-5
            checkTheta = np.arccos(np.clip( (intZ-e)/(np.sqrt(np.power((intX-c),2) +  np.power((intY-d),2) + np.power((intZ-e),2))), -1.0,1.0))
            #TODO: Verify the definition of Theta in this context compared to ATLAS, and whether the below measure is an accurate representative.
            vec1 = self.createVector([intZ, intY], [0, 0])
            vec2 = self.createVector([self.CavernZ[1], 0], [0, 0])
            checkTheta2 = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
            checkTheta2 = np.arccos(np.clip(checkTheta2, -1, 1)) # In radians

            vec1 = self.createVector([intX, intY], [position[0], position[1]])
            vec2 = self.createVector([self.CavernX[1], 0], [0, 0])
            checkPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
            checkPhi = np.sign(vec1[1])*np.arccos(np.clip(checkPhi, -1, 1)) # In radians

            if verbose:
                print("Checking direction between intersection and original point")
                print(f"Actual Theta, and projected Theta: {theta} | {checkTheta} | abs(checkTheta - theta) > {sanityThreshold}: {abs(checkTheta-theta)>sanityThreshold}")
                print(f"Actual Phi, and projected Phi: {phi} | {checkPhi} | abs(checkPhi - phi) > {sanityThreshold}: {abs(checkPhi-phi)>sanityThreshold}")

            # print(checkTheta, checkTheta2)
            if abs(checkTheta-theta)>sanityThreshold or abs(checkPhi-phi) > sanityThreshold:
                continue

            # Each Simple RPC layer could contain several RPC singlets within - loop over each.
            for iRPC in range(self.nRPCsPerLayer):
                # Then to simulate the detection efficiency of an RPC use a random number between 0 - 1, 
                # if it is below the RPCeff, then it will count as an intersection.
                hitVal = np.random.uniform(0,1)
                if ( hitVal <= self.RPCeff):
                    intersections.append((intX, intY, intZ))
                    nIntersections+=1

                    # Also save the intersecting station layer (and RPC in that layer) 
                    intersectionStations.append((i, iRPC))

        if verbose:
            print(f"Total Intersections: {nIntersections}")

        return nIntersections, intersections, intersectionStations
    
    def intersectANUBISstationsShaft(self, theta, phi, ANUBISstations, position=[], extremaPosition=[], verbose=False):
        #   - ANUBISstations in this case should provide a dictionary of the form: 
        #       {"x": [], "y": [[minY,maxY]...], "z": [], "RPCradius": [], "pipeCutoff": {"x": N, "z": M}
        #   - where the x, y and z mark the centre of a circular RPC of radius RPCradius, and the pipCutoff represents max LOCAL x and z for the circle.
        #   extremaPosition: gives the extrema (x,y,z) to constrain the projection of the intersection 
        #       i.e. For non-final state tracks that travel from production vertex (position) to decay vertex (extremaPosition)
        
        # Assume position (x,y,z) is provided relative to the cavern centre, if empty assume the particle came from IP
        if len(position)==0:
            position = (self.IP["x"], self.IP["y"], self.IP["z"])

        if verbose:
            print(f"Position (X,Y,Z): ({position})")
            print(f"Theta, Phi: {theta}, {phi}")

        nIntersections=0
        intersections=[]
        intersectingStations=[]
        for idx in range(len(ANUBISstations["x"])):
            passed=False
            if verbose:
                print("--------------")
                print(f"Station {idx} centre (x,y,z): ({ANUBISstations['x'][idx]},{ANUBISstations['y'][idx][0]},{ANUBISstations['z'][idx]})")   
                if phi>0:
                    print(f"(phi +ve) -> Y condition: {position[2]} < {ANUBISstations['y'][idx][0]}: {position[2] < ANUBISstations['y'][idx][0]}")
                else:
                    print(f"(phi -ve) -> Y condition: {position[2]} > {ANUBISstations['y'][idx][0]}: {position[2] > ANUBISstations['y'][idx][0]}")
            if (position[1] < ANUBISstations["y"][idx][0] and phi>=0) or\
               (position[1] > ANUBISstations["y"][idx][0] and phi<0): 
                # Require hit to be below tracking stations for upgoing tracks and vice verse

                # The projected X and Z locations relative to the centre of the RPC station.
                projX = ((ANUBISstations["y"][idx][0]-position[1]) / np.tan(phi)) + position[0] - ANUBISstations['x'][idx] 
                projZ = ((ANUBISstations["y"][idx][0]-position[1]) / np.tan(theta)) + position[2] - ANUBISstations['z'][idx]

                if verbose:
                    print(f"{idx} projX, projY, projZ: {projX} | {ANUBISstations['y'][idx][0]} | {projZ}")
                    print(f"rad: {np.sqrt(np.power(projX,2) + np.power(projZ,2))}  < {ANUBISstations['RPCradius'][idx]}?") 
                    print(f"Within RPC Layer Radius: {np.sqrt(np.power(projX,2) + np.power(projZ,2)) < ANUBISstations['RPCradius'][idx]}") 

                if (np.sqrt(np.power(projX,2) + np.power(projZ,2)) < ANUBISstations['RPCradius'][idx]):
                    passed=True

                    
                    # Check if the hit would intersect with the cut-out region of the RPC that allows pipes to go up the shaft
                    if "x" in ANUBISstations["pipeCutoff"].keys():
                        if ANUBISstations["pipeCutoff"]["x"] !="":
                            if verbose:
                                print(f"Projected X compared to cutoff:  {projX} | {ANUBISstations['pipeCutoff']['x']}")
                            if (((projX) < ANUBISstations["pipeCutoff"]["x"] and ANUBISstations["pipeCutoff"]["x"] < 0) or
                                ((projX) > ANUBISstations["pipeCutoff"]["x"] and ANUBISstations["pipeCutoff"]["x"] > 0)):
                                passed=False

                            if verbose:
                                print(f"XPassed: {passed}")
                    if "z" in ANUBISstations["pipeCutoff"].keys():
                        if ANUBISstations["pipeCutoff"]["z"] !="":
                            if verbose:
                                print(f"Projected Z compared to cutoff:  {projZ} | {ANUBISstations['pipeCutoff']['z']}")
                            if (((projZ) < ANUBISstations["pipeCutoff"]["z"] and ANUBISstations["pipeCutoff"]["z"] < 0) or
                                ((projZ) > ANUBISstations["pipeCutoff"]["z"] and ANUBISstations["pipeCutoff"]["z"] > 0)):
                                passed=False

                            if verbose:
                                print(f"ZPassed: {passed}")

                intX, intY, intZ = projX + ANUBISstations['x'][idx], ANUBISstations['y'][idx][0], projZ + ANUBISstations['z'][idx]
                
                # Check that projected intersection point does not exceed the extremaPosition if given
                if len(extremaPosition)!=0:
                    constrainedR = np.linalg.norm([extremaPosition[i]-position[i] for i in [0,1,2]]) 
                    intersectionR = np.linalg.norm([intX-position[0], intY-position[1], intZ-position[2]])

                    if verbose:
                        print(f"ConR, IntR: {constrainedR}, {intersectionR} | intR < constrainedR {intersectionR < constrainedR}")

                    passed = intersectionR < constrainedR

                    if verbose:
                        print(f"Checking that intersection points do not exceed extremaPosition constraint: {extremaPosition} | {passed}")
                    
                if passed:
                    # Each Simple RPC layer could contain several RPC singlets within - loop over each.
                    for iRPC in range(self.nRPCsPerLayer):
                        # Then to simulate the detection efficiency of an RPC use a random number between 0 - 1, 
                        # if it is below the RPCeff, then it will count as an intersection.
                        hitVal = np.random.uniform(0,1)
                        if ( hitVal <= self.RPCeff):
                            intersections.append((intX, intY, intZ))
                            nIntersections+=1
                            
                            # Also save the intersecting station layer (and RPC in that layer) 
                            intersectingStations.append((idx, iRPC))
                    if verbose:
                        print(f"Passed, appending intersection: {(projX + ANUBISstations['x'][idx], ANUBISstations['y'][idx][0], projZ + ANUBISstations['z'][idx])}") 
                        print("-----------")

        if verbose:
            print(f"{nIntersections} Intersections: {intersections}")

        return nIntersections, intersections, intersectingStations

    def SolidAngle(self, a, b, d):
        # Solid Angle of a rectangular Pyramid (See https://vixra.org/pdf/2001.0603v2.pdf, equation 27)
        alpha = a / (2*d)
        beta = b / (2*d)
        return 4*np.arctan( (alpha*beta) / np.sqrt(1 + alpha**2 + beta**2)) #sr

    def calculateAngles(self, relToCentre=False, verbose=True):
        # All Angles calculated relative to the IP unless relToCentre specified, then done relative to Cavern Centre
        if relToCentre:
            refX, refY, refZ = self.centreOfCurvature["x"], self.centreOfCurvature["y"], 0
            if verbose: print("Angles are being calculated relative to the Cavern Centre...")
        else:
            refX, refY, refZ = self.IP["x"], self.IP["y"], self.IP["z"]
            if verbose: print("Angles are being calculated relative to the IP...")

        # Phi in ATLAS coords (XY) relative to the x axis, phi=0 at y=0, +ve x and increases anti-clockwise
        phi=[]
        for i in [0,1]:
            # Corner of the cavern in XY space where Z is set to 0
            vec1 = self.createVector([self.CavernX[i],self.CavernY[1]], [refX, refY])
            vec2 = self.createVector([self.CavernX[1], refY], [refX, refY])
            tempPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
            phi.append(np.arccos(np.clip(tempPhi, -1, 1))) # In radians

        # Polar Angle in ATLAS coords (YZ), 0 when aligned with +ve z-axis
        theta=[]
        for i in [0,1]:
            # Corner of the cavern in YZ space where X is set to 0
            cornerY = self.obtainCavernYFromX(0) - refY
            vec1 = self.createVector([self.CavernZ[i], cornerY] , [refZ, refY])
            vec2 = self.createVector([self.CavernZ[1], refY], [refZ, refY])
            tempTheta = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
            theta.append(np.arccos(np.clip(tempTheta, -1, 1))) # In radians

        # Eta in ATLAS coords (YZ) 
        eta = [ (x/abs(x)) * -np.log(np.tan(abs(x)/2)) for x in theta]

        # Solid Angle
        a = self.CavernZLength
        b = self.CavernXLength
        d = self.CavernYLength/2 # Relative to the centre of the cavern
        # On Axis case: solidAngle = self.SolidAngle(a,b,d)
        if verbose:
            print(f"On Axis SolidAngle: {self.SolidAngle(a,b,d)}")
            print(f"On Axis SolidAngle Test: {self.SolidAngle(2*self.archRadius*(self.CavernZLength/self.CavernYLength),2*self.archRadius*(self.CavernXLength/self.CavernYLength),self.archRadius)}")
        # IP is Off-axis of the centre of the projected rectangle of the ceiling, 
        # use A and B to scale as in https://vixra.org/pdf/2001.0603v2.pdf, equation 34
        A = self.CavernZLength/2 
        B = abs(self.CavernXLength/2 + refX)
        d_IP = self.CavernYLength/2 - self.IP["y"]
        solidAngle = (self.SolidAngle(2*(a-A),2*(b-B),d_IP) + self.SolidAngle(2*A,2*(b-B),d_IP) + self.SolidAngle(2*(a-A),2*B,d_IP) + self.SolidAngle(2*A,2*B,d_IP) ) /4

        return {"phi": phi, "phiRange": abs(phi[0])+abs(phi[1]),\
                "theta": theta, "thetaRange": abs(theta[1] - theta[0]),\
                "eta": eta, "etaRange": abs(eta[0])+abs(eta[1]),\
                "solidAngle": solidAngle} 

    #--------------------------#
    #   Plotting Functions     #
    #--------------------------#
    # Create a grid of points within the Access Shafts 
    def createAccessShafts(self):
        theta = np.linspace(0, 2*np.pi, 100)
        y_PX14 = np.linspace(self.PX14_Centre["y"],self.PX14_Centre["y"]+self.PX14_Height,100)
        gridTheta_PX14, gridY_PX14 = np.meshgrid(theta, y_PX14)
        gridX_PX14 = self.PX14_Radius*np.cos(gridTheta_PX14) + self.PX14_Centre["x"]
        gridZ_PX14 = self.PX14_Radius*np.sin(gridTheta_PX14) + self.PX14_Centre["z"]

        y_PX16 = np.linspace(self.PX16_Centre["y"],self.PX16_Centre["y"]+self.PX16_Height,100)
        gridTheta_PX16, gridY_PX16 = np.meshgrid(theta, y_PX16)
        gridX_PX16 = self.PX16_Radius*np.cos(gridTheta_PX16) + self.PX16_Centre["x"]
        gridZ_PX16 = self.PX16_Radius*np.sin(gridTheta_PX16) + self.PX16_Centre["z"]

        return { "PX14": {"x": gridX_PX14, "y": gridY_PX14, "z": gridZ_PX14},\
                 "PX16": {"x": gridX_PX16, "y": gridY_PX16, "z": gridZ_PX16} }

    # Plot the Cavern Ceiling -- deprecated with plotFullATLASCavern
    def createCavernVault(self, doPlot=True):
        archX =  np.linspace(self.CavernX[0], self.CavernX[1], 100)
        archY = []
        for x in archX:
            archY.append(np.sqrt(np.power(self.archRadius,2) - np.power(x,2)) + self.centreOfCurvature["y"])
        
        archZ =  np.linspace(self.CavernZ[0], self.CavernZ[1], 100)

        if doPlot:
            #XY at Z=0
            fig, ax = plt.subplots(1, figsize=(16, 10), dpi=100)
            ax.scatter(archX, archY, c="paleturquoise")
            plt.xlabel("x /m")
            plt.ylabel("y /m")
            plt.title("ATLAS Cavern Ceiling at z=0m")
            plt.tight_layout()
            plt.savefig("cavernCeiling_XY.pdf")
            plt.close()

            #XZ at Y = CavernYLength/2 
            fig, ax = plt.subplots(1, figsize=(16, 10), dpi=100)
            ax.scatter(archX, archZ, c="paleturquoise")
            plt.Circle((self.PX14_Centre["x"], self.PX14_Centre["z"]), self.PX14_Radius, color="blue", fill=False)
            ax.annotate("PX14", xy = (self.PX14_Centre["x"], self.PX14_Centre["z"]), fontsize=20, ha="center")
            plt.Circle((self.PX16_Centre["x"], self.PX16_Centre["z"]), self.PX16_Radius, color="blue", fill=False)
            ax.annotate("PX16", xy = (self.PX16_Centre["x"], self.PX16_Centre["z"]), fontsize=20, ha="center")
            plt.xlabel("x /m")
            plt.ylabel("z /m")
            plt.title(f"ATLAS Cavern Ceiling at y={self.CavernYLength/2}m")
            plt.tight_layout()
            plt.savefig("cavernCeiling_XZ.pdf")
            plt.close()

            #3D Plot
            fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
            
            xx, zz = np.meshgrid(archX, archZ)

            mask = np.logical_and(np.sqrt((xx-self.PX14_Centre["x"])**2 + (zz-self.PX14_Centre["z"])**2) > self.PX14_Radius, 
                                    np.sqrt((xx-self.PX16_Centre["x"])**2 + (zz-self.PX16_Centre["z"])**2) > self.PX16_Radius)

            xx[~mask] = np.nan
            zz[~mask] = np.nan
            yy = np.sqrt(np.power(self.archRadius,2) - np.power(xx-self.centreOfCurvature["x"],2))
            #yy[mask] = np.nan
            
            ax.plot_surface(xx, zz, yy, rstride=4, cstride=4, alpha=0.25)
            plt.xlabel("x /m")
            plt.ylabel("z /m")
            ax.set_zlabel("y /m")
            plt.tight_layout()
            plt.savefig("cavernCeiling_XYZ.pdf")
            plt.close()

        return {"x": archX, "y": archY, "z": archZ}

    def convertRPCList(self, rpcList):
        # Convert a list of RPCs with the following info:
        #   - corners: 8 (x,y,z) coordinates corresponding to their corners, 
        #   - midPoint: The midPoint of the RPC in (x,y,z), 
        #   - "LayerID" and "RPCid": A Layer ID and RPC ID to uniquely identify the RPC
        #   - "plane": A Sympy plane in the eta-phi plane that passes through the midpoint
        # To a total set of lists for each entry
        
        corners, midPoints, layerIDs, RPCIDs, planes = [], [], [], [], []
        for rpc in rpcList:
            corners.append(rpc["corners"])
            midPoints.append(rpc["midPoint"])
            layerIDs.append(rpc["LayerID"])
            RPCIDs.append(rpc["RPCid"])
            planes.append(rpc["plane"])

        return {"corners": corners, "midPoint": midPoints, "LayerID": layerIDs, "RPCid": RPCIDs, "plane": planes} 

    from _plotGeometry import plotCavernXY, plotCavernXZ, plotCavernZY, plotCavern3D, plotRPCsXY, plotRPCsXZ, plotRPCsZY, plotRPCs3D,\
                              plotSimpleRPCsXY, plotHitsHist, plotHitsScatter, plotShaftRPCsXY, plotShaftRPCsXZ, plotShaftRPCsZY, plotShaftRPCs3D

    # Plot all features of the ATLAS Cavern, plus additional features if provided: e.g. ANUBIS.
    def plotFullCavern(self, hits={}, anubisRPCs=[], simpleAnubisRPCs=[], shaftAnubisRPCs=[], plotRPCs={"xy": True, "xz": False, "zy": False, "3D": False},
                             ranges={"xy": {}, "xz": {}, "zy": {}, "3D": {}}, plotFailed=True, plotATLAS=False, plotAcceptance=False, 
                             suffix="", outDir="./plots"):
        if len(hits)!=0:
            failedHits={"x": [x[0] for x in hits["failed"]],
                        "y": [y[1] for y in hits["failed"]],
                        "z": [z[2] for z in hits["failed"]], 
            }
            passedHits={"x": [x[0] for x in hits["passed"]],
                        "y": [y[1] for y in hits["passed"]],
                        "z": [z[2] for z in hits["passed"]], 
            }

        #XY
        fig, ax = plt.subplots(1, figsize=(10, 16), dpi=100)
        self.plotCavernXY(ax, plotATLAS=plotATLAS, plotAcceptance=plotAcceptance) 
        if len(simpleAnubisRPCs)!=0 and plotRPCs["xy"]:
            self.plotSimpleRPCsXY(ax, simpleAnubisRPCs)
        if len(shaftAnubisRPCs)!=0 and plotRPCs["xy"]:
            self.plotShaftRPCsXY(ax, shaftAnubisRPCs)
        if len(anubisRPCs)!=0 and plotRPCs["xy"]:
            self.plotRPCsXY(ax, anubisRPCs)
        if len(hits)!=0:
            counts, xedges, yedges, im = ax.hist2d(passedHits["x"], passedHits["y"], 
                                                  range=(hits["bins"]["rangeX"],hits["bins"]["rangeY"]), bins = (hits["bins"]["nX"], hits["bins"]["nY"]), cmin=1)
            cbar = plt.colorbar(im, fraction=0.046, pad=0.04, ax=ax)
            if plotFailed:
                ax.scatter(failedHits["x"], failedHits["y"], c="r", marker="x")

        plt.xlabel(f"x /m")
        plt.ylabel(f"y /m")
        plt.title("ATLAS Cavern")
        if len(ranges["xy"])==0:
            ax.set_xlim(-18,18)
            
            if len(shaftAnubisRPCs)!=0:
                ax.set_ylim(-15, 1.1*(self.PX14_Centre["y"]+self.PX14_Height))
            else:
                ax.set_ylim(-15,25)

            plt.savefig(f"{outDir}/ATLASCavern_XY_withShafts{suffix}.pdf", bbox_inches="tight")
            plt.gca().set_aspect('equal')
            ax.set_ylim(top=24)

            if len(shaftAnubisRPCs)==0:
                plt.savefig(f"{outDir}/ATLASCavern_XY{suffix}.pdf", bbox_inches="tight")
                ax.set_xlim(-16,-5)
                ax.set_ylim(10,20)
                plt.gca().set_aspect('auto')
                plt.savefig(f"{outDir}/ATLASCavern_XY_Zoomed{suffix}.pdf", bbox_inches="tight")
        else:
            ax.set_xlim(ranges["xy"]["x"])
            ax.set_ylim(ranges["xy"]["y"])
            plt.gca().set_aspect('auto')
            plt.savefig(f"{outDir}/ATLASCavern_XY{suffix}.pdf", bbox_inches="tight")
        plt.close(fig)

        #XZ
        fig2, ax2 = plt.subplots(1, figsize=(14, 14), dpi=100)
        if len(hits)!=0:
            counts2, xedges2, yedges2, im2 = ax2.hist2d(passedHits["x"], passedHits["z"],
                                                  range=(hits["bins"]["rangeX"],hits["bins"]["rangeZ"]), bins = (hits["bins"]["nX"], hits["bins"]["nZ"]), cmin=1)
            cbar = plt.colorbar(im2, fraction=0.046, pad=0.04, ax=ax2)
            if plotFailed:
                ax2.scatter(failedHits["x"], failedHits["y"], c="r", marker="x")
        
        self.plotCavernXZ(ax2, plotATLAS=plotATLAS) 
        if len(anubisRPCs)!=0 and plotRPCs["xz"]:
            self.plotRPCsXZ(ax2, anubisRPCs)
        if len(shaftAnubisRPCs)!=0 and plotRPCs["xz"]:
            self.plotShaftRPCsXZ(ax2, shaftAnubisRPCs)

        plt.xlabel(f"x /m")
        plt.ylabel(f"z /m")
        plt.title("ATLAS Cavern")
        if len(ranges["xz"])==0:
            ax2.set_xlim(-18,18)
            ax2.set_ylim(-30,30)
        else: 
            ax2.set_xlim(ranges["xz"]["x"])
            ax2.set_ylim(ranges["xz"]["z"])
        plt.gca().set_aspect('auto')
        plt.savefig(f"{outDir}/ATLASCavern_XZ{suffix}.pdf", bbox_inches="tight")
        plt.close(fig2)

        #ZY
        fig3, ax3 = plt.subplots(1, figsize=(16, 10), dpi=100)
        self.plotCavernZY(ax3, plotATLAS=plotATLAS, plotAcceptance=plotAcceptance) 
        if len(anubisRPCs)!=0 and plotRPCs["zy"]:
            self.plotRPCsZY(ax3, anubisRPCs)
        if len(shaftAnubisRPCs)!=0 and plotRPCs["zy"]:
            self.plotShaftRPCsZY(ax3, shaftAnubisRPCs)
        if len(hits)!=0:
            counts3, xedges3, yedges3, im3 = ax3.hist2d(passedHits["z"], passedHits["y"],
                                                  range=(hits["bins"]["rangeZ"],hits["bins"]["rangeY"]), bins = (hits["bins"]["nZ"], hits["bins"]["nY"]), cmin=1)
            cbar3 = plt.colorbar(im3, fraction=0.046, pad=0.04, ax=ax3)
            if plotFailed:
                ax3.scatter(failedHits["z"], failedHits["y"], c="r", marker="x")
        plt.xlabel(f"z /m")
        plt.ylabel(f"y /m")
        plt.title("ATLAS Cavern")
        if len(ranges["zy"])==0:
            ax3.set_xlim(-30,30)
            if len(shaftAnubisRPCs)!=0:
                ax3.set_ylim(-15, 1.1*(self.PX14_Centre["y"]+self.PX14_Height))
            else:
                ax3.set_ylim(-15,25)
        else:
            ax3.set_xlim(ranges["zy"]["z"])
            ax3.set_ylim(ranges["zy"]["y"])
        plt.gca().set_aspect('auto')
        plt.savefig(f"{outDir}/ATLASCavern_ZY{suffix}.pdf", bbox_inches="tight")
        plt.close(fig3)

        #3D Plot
        fig4, ax4 = plt.subplots(subplot_kw={"projection": "3d"})
        self.plotCavern3D(ax4, plotATLAS=plotATLAS, plotAcceptance=plotAcceptance) 
        if len(anubisRPCs)!=0 and plotRPCs["3D"]:
            self.plotRPCs3D(ax4, anubisRPCs)
        if len(shaftAnubisRPCs)!=0 and plotRPCs["3D"]:
            self.plotShaftRPCs3D(ax4, shaftAnubisRPCs)
        if len(hits)!=0:
            ax4.scatter(passedHits["x"], passedHits["z"], passedHits["y"], c="lime", marker="^")
            if plotFailed:
                ax4.scatter(passedHits["x"], passedHits["z"], passedHits["y"], c="red", marker="x")
        plt.xlabel(f"z /m")
        plt.ylabel(f"y /m")
        ax4.set_zlabel("y /m")
        plt.tight_layout()
        if len(ranges["3D"])==0:
            ax4.set_xlim(-30,30)
            ax4.set_ylim(-30,30)
            ax4.set_zlim(-30,30)
        else:
            ax4.set_xlim(ranges["3D"]["x"])
            ax4.set_ylim(ranges["3D"]["z"])
            ax4.set_zlim(ranges["3D"]["y"])
        plt.savefig(f"{outDir}/ATLASCavern_XYZ{suffix}.pdf")
        plt.close(fig4)


    def ANUBIS_RPC_positions(self, RPCx=1, RPCy=0.06, RPCz=1.8, overlapAngleXY=0, overlapZ=0, startTheta=-999, layerRadius=0, ID=0):
        #RPC{x,y,z} are the lengths in those directions in the ATLAS Cavern coordinate system used here
        RPCs=[]

        if layerRadius==0:
            layerRadius = self.archRadius - (RPCy/2) # RPC attaches to the ceiling.

        if startTheta==-999:
            # Assume starting on the corner of the ceiling 
            totalTheta = 2*np.arcsin( self.CavernXLength/(2*layerRadius)) # Relative to centre of curvature.
            theta= -totalTheta/2
        else:
            # Assume full ceiling coverage starting from the initial theta value: which is 0 at the vertical x=0
            halfTheta = np.arcsin( self.CavernXLength/(2*layerRadius)) # Relative to centre of curvature.

            if halfTheta < startTheta:
                raise Exception(f"Attempting to start beyond the limit of the ATLAS Cavern at theta of {startTheta}")

            totalTheta = halfTheta - startTheta
            theta = startTheta
            

        # XY positions
        #   - Find the angular size of the RPC to segment the ceiling with
        #   - Each RPC position includes the two corners of the RPC and the midpoint. 
        #   - Effectively unravelling the ceiling into a straight line.
        dTheta = 2*np.arcsin( RPCx/(2*layerRadius))
        Nsegments = np.ceil( totalTheta / (dTheta - overlapAngleXY) ) #Not sure this is correct 

        breakCon = True
        xPos, yPos = [], []
        nIter=0
        while breakCon:
            # Step through theta in units of dTheta - overlap angle
            # Get (x,y) coord of centre of angular segment and save to list
            if nIter == 0:
                overlapTheta = 0
            else:
                overlapTheta = overlapAngleXY 

            tempTheta = theta + (dTheta - overlapTheta)/2 # Midpoint of RPC segment
            if tempTheta > totalTheta/2 or (theta+dTheta) > totalTheta:
                breakCon=False
                break

            bottomOfRPC = layerRadius * np.cos(dTheta/2) - RPCy
            # Convert to cartesian positions with x = r*sin(theta), y = r*cos(theta) relative to Cavern centre
            tempXPos = {"c1": layerRadius*np.sin(theta) + self.centreOfCurvature["x"], 
                        "c2": layerRadius*np.sin(theta + (dTheta - overlapTheta)) + self.centreOfCurvature["x"],
                        "c3": bottomOfRPC*np.sin(theta) + self.centreOfCurvature["x"], 
                        "c4": bottomOfRPC*np.sin(theta + (dTheta - overlapTheta)) + self.centreOfCurvature["x"],
                        "mid": (layerRadius*np.cos(dTheta/2) - (0.5*RPCy))*np.sin(tempTheta) + self.centreOfCurvature["x"],
                        "midTop": layerRadius*np.sin(theta + ((dTheta/2) - overlapTheta)) + self.centreOfCurvature["x"],
            }

            tempYPos = {"c1": layerRadius*np.cos(theta) + self.centreOfCurvature["y"], 
                        "c2": layerRadius*np.cos(theta + (dTheta - overlapTheta)) + self.centreOfCurvature["y"],
                        "c3": bottomOfRPC*np.cos(theta) + self.centreOfCurvature["y"], 
                        "c4": bottomOfRPC*np.cos(theta + (dTheta - overlapTheta)) + self.centreOfCurvature["y"],
                        "mid": (layerRadius*np.cos(dTheta/2) - (0.5*RPCy))*np.cos(tempTheta) + self.centreOfCurvature["y"],
                        "midTop": layerRadius*np.cos(theta + ((dTheta/2) - overlapTheta)) + self.centreOfCurvature["y"],
                        }
            

            xPos.append(tempXPos)
            yPos.append(tempYPos)

            # increment to the next corner of the RPC segments
            theta+=(dTheta - overlapAngleXY)
            
            if theta > totalTheta/2:
                breakCon=False
                break

            nIter+=1

        print(f"There were {nIter} Iterations...")

        #Z Positions:
        breakCon2 = True
        zPos=[]
        Z = self.CavernZ[0]
        nIter2=0
        while breakCon2:
            if nIter2 == 0:
                overlap = 0
            else:
                overlap = overlapZ

            tempZ = Z + ((RPCz-overlap)/2) #Midpoint of RPC
            if tempZ > self.CavernZ[1] or (Z + (RPCz-overlap)) > self.CavernZ[1]:
                breakCon2 = False
                break
            
            zPos.append({"c1": Z, "c2": Z + RPCz - overlap, "mid": tempZ})

            # increment to next RPC segment
            Z+= RPCz - overlap
            if Z > self.CavernZ[1]:
                breakCon2 = False
                break

            nIter2+=1

        print(f"There were {nIter2} Iterations...")


        # Create a list of RPC stations, each with: 
        #   - corners: 8 (x,y,z) coordinates corresponding to their corners, 
        #   - midPoint: The midPoint of the RPC in (x,y,z), 
        #   - "LayerID" and "RPCid": A Layer ID and RPC ID to uniquely identify the RPC
        #   - "plane": A Sympy plane in the eta-phi plane that passes through the midpoint
        posRPC={"x": {"c1": [], "c2": [], "c3": [], "c4": [], "mid": []}, 
                "y": {"c1": [], "c2": [], "c3": [], "c4": [], "mid": []},
                "z": {"c1": [], "c2": [], "mid": []},
        }
        rpcID=0
        for coordZ in zPos:
            for coordX, coordY in zip(xPos, yPos):
                #   Below is a representation of which corner in (x,y,z) each element of the corners list corresponds to.
                #
                #             1--------3
                #            /|       /|
                #           / |      / |
                #          0--------2  |
                #          |  5-----|--7
                # y        | /      | /
                # | z      |/       |/
                # |/       4--------6
                # o--x
                corners=[ (coordX["c1"], coordY["c1"], coordZ["c1"]),
                          (coordX["c1"], coordY["c1"], coordZ["c2"]),
                          (coordX["c2"], coordY["c2"], coordZ["c1"]),
                          (coordX["c2"], coordY["c2"], coordZ["c2"]),
                          (coordX["c3"], coordY["c3"], coordZ["c1"]),
                          (coordX["c3"], coordY["c3"], coordZ["c2"]),
                          (coordX["c4"], coordY["c4"], coordZ["c1"]),
                          (coordX["c4"], coordY["c4"], coordZ["c2"]), ]

                midPoint = (coordX["mid"], coordY["mid"], coordZ["mid"])

                # Define a plane using three points on the top of the RPC segment
                plane = Plane( (coordX["c1"], coordY["c1"],coordZ["mid"]),
                               (coordX["c2"], coordY["c2"],coordZ["mid"]),
                               (coordX["midTop"], coordY["midTop"],coordZ["mid"]))

                RPCs.append( {"corners": corners, "midPoint": midPoint, "plane": plane, "RPCid": rpcID, "LayerID": ID} )
                rpcID+=1

        self.ANUBIS_RPCs = RPCs
        self.geoMode = "fullCeiling"

        return RPCs

    def createSimpleRPCs(self, radii, RPCthickness=0.06):#, origin=[]):

        # Save the RPC angular coverage both relative to the IP and the Centre of Curvature (CoC) 
        RPCs={"r": [], "theta": {"CoC": [], "IP": []}, "phi": {"CoC": [], "IP": []}}

        # Radii are assumed to be relative to the centre of curvature
        tempAngles={}
        tempAngles["CoC"] = self.calculateAngles(relToCentre=True, verbose=False)
        tempAngles["IP"] = self.calculateAngles(relToCentre=False, verbose=False)
        for r in radii:
            RPCs["r"].append( [r - RPCthickness, r] )
            for angleRef in ["CoC", "IP"]:
                if angleRef=="IP":
                    origin = (self.IP["x"], self.IP["y"], self.IP["z"])
                elif angleRef=="CoC":
                    origin = (self.centreOfCurvature["x"], self.centreOfCurvature["y"], 0)

                #RPCs["theta"][angleRef].append([min(tempAngles[angleRef]["theta"]), max(tempAngles[angleRef]["theta"])])
                thetaList=[]
                for i in [1,0]:
                    # Getting minimum Y values to get max theta coverage: This is on the X boundaries of the cavern.
                    cornerY = np.sqrt((r**2) - ((self.CavernX[i] - self.centreOfCurvature["x"])**2)) + self.centreOfCurvature["y"]
                    vec1 = self.createVector([self.CavernZ[i], cornerY], [origin[2], origin[1]])
                    vec2 = self.createVector([self.CavernZ[1], origin[1]], [origin[2], origin[1]])
                    tempTheta = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    thetaList.append(np.arccos(np.clip(tempTheta, -1, 1))) # In radians
                
                    RPCs["theta"][angleRef].append(thetaList)

                if r < abs(self.CavernX[0]-self.centreOfCurvature["x"]):
                    RPCs["phi"][angleRef].append([0,2*np.pi]) # As in this case you get a circle within the ATLAS Cavern
                else:
                    phiList=[]
                    for i in [1,0]:
                        cornerY = np.sqrt((r**2) - ((self.CavernX[i] - self.centreOfCurvature["x"])**2)) + self.centreOfCurvature["y"]
                        vec1 = self.createVector([self.CavernX[i], cornerY], [origin[0], origin[1]])
                        vec2 = self.createVector([self.CavernX[1], origin[1]], [origin[0], origin[1]])
                        tempPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                        phiList.append(np.arccos(np.clip(tempPhi, -1, 1))) # In radians
                    
                    RPCs["phi"][angleRef].append(phiList)

        self.ANUBIS_RPCs = RPCs
        self.geoMode = "ceiling"

        return RPCs

    def createShaftRPCs(self, heights, RPCradius={"PX14": -1, "PX16": -1}, RPCthickness=0.06, clearance=0.25,
                        pipeCutoff={"x":-7.25, "z": ""}, shafts=["PX14"], includeCone=False):
        # For the shaft there are a set of circular stations at different heights, with a defined xz cutoff to allow pipes to pass through
        # - Assume that the heights are given as the bottom of the RPC - relative to the base of the shaft  

        RPCs={"x": [], "y": [], "z": [], "RPCradius": [], "pipeCutoff": pipeCutoff} 
        # The above dict defines the centre of the circular RPC stations, their radius and any cutoffs to be applied.
        # - The y parameter is a list representing the max and min due to the thickness of the RPC
        for shaft in shafts:
            if (RPCradius[shaft] > self.shaftParams[shaft]["radius"]):
                print(f"RPC radius is set larger than the {shaft} shaft radius, reducing it to fit within the shaft with a clearance of {clearance} m")
                RPCradius[shaft] = -1

            if RPCradius[shaft] == -1: 
                RPCradius[shaft] = self.shaftParams[shaft]["radius"] - clearance

            for height in heights: 
                if (height + RPCthickness > self.shaftParams[shaft]["height"]):
                    print(f"Trying to place RPCs above the shaft, skipping for height {height}")
                    continue
                
                RPCs["x"].append(self.shaftParams[shaft]["Centre"]["x"])
                RPCs["z"].append(self.shaftParams[shaft]["Centre"]["z"])
                RPCs["y"].append([height + self.shaftParams[shaft]["Centre"]["y"], height + self.shaftParams[shaft]["Centre"]["y"] + RPCthickness])
                RPCs["RPCradius"].append(RPCradius[shaft])

            print(RPCs["y"])

        self.ANUBIS_RPCs = RPCs
        self.geoMode = "shaft"
        if includeCone:
            self.geoMode+="+cone"

        return RPCs


if __name__=="__main__":
    import argparse
    import datetime
    parser = argparse.ArgumentParser(description='Provide an input file')
    parser.add_argument('--remake', action='store_true')
    parser.add_argument('--mode', type=str, choices=["", "full", "simple", "shaft"])
    parser.add_argument('--suffix', type=str, default="")
    args = parser.parse_args()

    print(datetime.datetime.now())
    cav = ATLASCavern()
    #cav.createCavernVault()

    print(f"Cavern Bounds: {cav.CavernBounds}")
    print(f"Cavern Corners: {cav.CavernCorners}")
    print(f"IP Location: {cav.IP}")
    print(f"Centre of Curvature: {cav.centreOfCurvature}")
    print(cav.angles)

    #cav.plotFullCavern(plotATLAS=True, plotAcceptance=True, plotFailed=False, suffix=f"{args.suffix}")

    # Create ANUBIS RPC Layers
    #   - Afterwards save to a pickle file. 
    #   - Reload RPCs from pickle file if it exists.
    
    if args.mode in ["", "full"]:
        pickleDir = "./pickles"
        if not os.path.exists(pickleDir):
            os.makedirs(pickleDir)

        print("Making RPC Layers...")
        print(datetime.datetime.now())
        if not os.path.exists(f"{pickleDir}/ANUBIS_RPCs_Layer0.pickle") or args.remake:
            #Layer of RPCs (Triplet) attached to the ceiling.
            RPC_Pos1 = cav.ANUBIS_RPC_positions(RPCx=1, RPCy=0.06, RPCz=1.8, overlapAngleXY=0, overlapZ=0, layerRadius = cav.archRadius, ID=0)
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer0.pickle", "wb") as pkl:
                pickle.dump(RPC_Pos1, pkl)
        else:
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer0.pickle", "rb") as pkl:
                RPC_Pos1 = pickle.load(pkl)

        if not os.path.exists(f"{pickleDir}/ANUBIS_RPCs_Layer1.pickle") or args.remake:
            #Singlet RPCs between the Triplets (40cm below Top Triplet).
            RPC_Pos2 = cav.ANUBIS_RPC_positions(RPCx=1, RPCy=0.06, RPCz=1.8, overlapAngleXY=0, overlapZ=0, layerRadius = cav.archRadius-0.40, ID=0)
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer1.pickle", "wb") as pkl:
                pickle.dump(RPC_Pos2, pkl)
        else:
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer1.pickle", "rb") as pkl:
                RPC_Pos2 = pickle.load(pkl)

        if not os.path.exists(f"{pickleDir}/ANUBIS_RPCs_Layer2.pickle") or args.remake:
            #Bottom Triplet RPCs (1m below Top Triplet).
            RPC_Pos3 = cav.ANUBIS_RPC_positions(RPCx=1, RPCy=0.06, RPCz=1.8, overlapAngleXY=0, overlapZ=0, layerRadius = cav.archRadius-1, ID=0)
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer2.pickle", "wb") as pkl:
                pickle.dump(RPC_Pos3, pkl)
        else:
            with open(f"{pickleDir}/ANUBIS_RPCs_Layer2.pickle", "rb") as pkl:
                RPC_Pos3 = pickle.load(pkl)

        print("Checking hit intersections...")
        hitStart1=datetime.datetime.now()
        print(hitStart1)
        hitBins = {"nX": 100, "nY": 100, "nZ": 100}
        # Check whether a set of points intersect ANUBIS
        x = np.linspace(cav.CavernX[0] - 5, cav.CavernX[1] + 5, hitBins["nX"])
        y = np.linspace(cav.CavernY[0] - 5, (cav.archRadius + cav.centreOfCurvature["y"]) + 5, hitBins["nY"])
        z = np.linspace(cav.CavernZ[0] - 5, cav.CavernZ[1] + 5, hitBins["nZ"])

        hitBins["widthX"] = abs(x[1]-x[0])
        hitBins["widthY"] = abs(y[1]-y[0])
        hitBins["widthZ"] = abs(z[1]-z[0])
        hitBins["rangeX"] = [x[0]-(hitBins["widthX"]/2), x[-1]+(hitBins["widthX"]/2)]
        hitBins["rangeY"] = [y[0]-(hitBins["widthY"]/2), y[-1]+(hitBins["widthY"]/2)]
        hitBins["rangeZ"] = [z[0]-(hitBins["widthZ"]/2), z[-1]+(hitBins["widthZ"]/2)]
        
        ANUBISstations = RPC_Pos1
        ANUBISstations.extend(RPC_Pos2)
        ANUBISstations.extend(RPC_Pos3)
        ANUBISstations = cav.convertRPCList(ANUBISstations)

        nHits=0
        passedHits, failedHits = [], []
        for X in x:
            for Y in y:
                for Z in z:
                    #print(f"Before Intersection: {datetime.datetime.now()}")
                    inCavern = cav.inCavern(X, Y, Z)
                    inATLAS = cav.inATLAS(X, Y, Z, trackingOnly=False)
                    intANUBIS = cav.intersectANUBISstations(X, Y, Z, ANUBISstations, origin=[])

                    if ( inCavern and not inATLAS and (len(intANUBIS[1]) >= 2) ):
                        passedHits.append((X,Y,Z))
                    else:
                        failedHits.append((X,Y,Z))
                    #print(f"After Intersection: {datetime.datetime.now()}")
                    print(f"{nHits}/{len(x)*len(y)*len(z)}")
                    nHits+=1
                    #input("...")

        hitEnd1=datetime.datetime.now()
        print(hitEnd1)
        #print(f"Took {hitEnd1 - hitStart1}")

    if args.mode in ["", "simple"]:
        hitStart2=datetime.datetime.now()
        print(hitStart2)
        ANUBISstations = cav.createSimpleRPCs([cav.archRadius-0.2, cav.archRadius-0.6, cav.archRadius-1.2], RPCthickness=0.06)
        minStationRadius = min(min(ANUBISstations["r"]))

        hitBins = {"nX": 100, "nY": 100, "nZ": 100}
        x = np.linspace(cav.CavernX[0] - 5, cav.CavernX[1] + 5, hitBins["nX"])
        y = np.linspace(cav.CavernY[0] - 5, (cav.archRadius + cav.centreOfCurvature["y"]) + 5, hitBins["nY"])
        z = np.linspace(cav.CavernZ[0] - 5, cav.CavernZ[1] + 5, hitBins["nZ"])

        hitBins["widthX"] = abs(x[1]-x[0])
        hitBins["widthY"] = abs(y[1]-y[0])
        hitBins["widthZ"] = abs(z[1]-z[0])
        hitBins["rangeX"] = [x[0]-(hitBins["widthX"]/2), x[-1]+(hitBins["widthX"]/2)]
        hitBins["rangeY"] = [y[0]-(hitBins["widthY"]/2), y[-1]+(hitBins["widthY"]/2)]
        hitBins["rangeZ"] = [z[0]-(hitBins["widthZ"]/2), z[-1]+(hitBins["widthZ"]/2)]

        nHits=0
        passedHits, failedHits = [], []
        for X in x:
            for Y in y:
                for Z in z:
                    print(f"{nHits}/{len(x)*len(y)*len(z)}", end="\r", flush=True)
                    inCavern = cav.inCavern(X, Y, Z, maxRadius=minStationRadius - 0.20)
                    inATLAS = cav.inATLAS(X, Y, Z, trackingOnly=True)

                    vec1 = cav.createVector([X,Y], [cav.IP["x"], cav.IP["y"]])
                    vec2 = cav.createVector([cav.CavernX[1], cav.IP["y"]], [cav.IP["x"], cav.IP["y"]])
                    tempPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    phi = np.arccos(np.clip(tempPhi, -1, 1)) # In radians

                    vec1 = cav.createVector([Z,Y], [cav.IP["z"], cav.IP["y"]])
                    vec2 = cav.createVector([cav.CavernZ[1], cav.IP["y"]], [cav.IP["z"], cav.IP["y"]])
                    tempTheta = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    theta = np.arccos(np.clip(tempTheta, -1, 1)) # In radians

                    intANUBIS = cav.intersectANUBISstationsSimple(theta, phi, ANUBISstations, position=[X,Y,Z])

                    if ( inCavern and not inATLAS and (len(intANUBIS[1]) >= 2) ):
                        passedHits.append((X,Y,Z))
                    else:
                        failedHits.append((X,Y,Z))
                    nHits+=1

        hitEnd2=datetime.datetime.now()
        print(hitEnd2)
        print(f"Took {hitEnd2 - hitStart2}")
        print(f"Passed: {len(passedHits)} ({len(passedHits)/(len(passedHits)+len(failedHits))}) |"
              f"Failed: {len(failedHits)} ({len(failedHits)/(len(passedHits)+len(failedHits))})")

        print("plotting...")
        cav.plotFullCavern(simpleAnubisRPCs=ANUBISstations, plotATLAS=True, plotAcceptance=True, plotFailed=False, 
                                       hits={"passed": passedHits, "failed": failedHits, "bins": hitBins}, suffix=f"_SimpleWithHits{args.suffix}")
        print(datetime.datetime.now())


    if args.mode in ["", "shaft"]:
        hitStart3=datetime.datetime.now()
        print(hitStart3)

        ANUBISstations = cav.createShaftRPCs([0,1,18.5,19.5,37,38,55.5,56.5], RPCthickness=0.06, includeCone=True)

        hitBins = {"nX": 100, "nY": 150, "nZ": 100}
        x = np.linspace(cav.CavernX[0] - 5, cav.CavernX[1] + 5, hitBins["nX"])
        y = np.linspace(cav.CavernY[0] - 5, (cav.archRadius + cav.centreOfCurvature["y"]) + cav.shaftParams["PX14"]["height"], hitBins["nY"])
        z = np.linspace(cav.CavernZ[0] - 5, cav.CavernZ[1] + 5, hitBins["nZ"])

        hitBins["widthX"] = abs(x[1]-x[0])
        hitBins["widthY"] = abs(y[1]-y[0])
        hitBins["widthZ"] = abs(z[1]-z[0])
        hitBins["rangeX"] = [x[0]-(hitBins["widthX"]/2), x[-1]+(hitBins["widthX"]/2)]
        hitBins["rangeY"] = [y[0]-(hitBins["widthY"]/2), y[-1]+(hitBins["widthY"]/2)]
        hitBins["rangeZ"] = [z[0]-(hitBins["widthZ"]/2), z[-1]+(hitBins["widthZ"]/2)]

        nHits=0
        passedHits, failedHits = [], []
        for X in x:
            for Y in y:
                for Z in z:
                    print(f"{nHits}/{len(x)*len(y)*len(z)}", end="\r", flush=True)
                    #inCavern = cav.inCavern(X, Y, Z, maxRadius=minStationRadius - 0.20)
                    inShaft = cav.inShaft(X, Y, Z, includeCavernCone="cone" in cav.geoMode)
                    inATLAS = cav.inATLAS(X, Y, Z, trackingOnly=True)

                    vec1 = cav.createVector([X,Y], [cav.IP["x"], cav.IP["y"]])
                    vec2 = cav.createVector([cav.CavernX[1], cav.IP["y"]], [cav.IP["x"], cav.IP["y"]])
                    tempPhi = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    phi = np.arccos(np.clip(tempPhi, -1, 1)) # In radians

                    vec1 = cav.createVector([Z,Y], [cav.IP["z"], cav.IP["y"]])
                    vec2 = cav.createVector([cav.CavernZ[1], cav.IP["y"]], [cav.IP["z"], cav.IP["y"]])
                    tempTheta = np.dot(vec1, vec2) / ( np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    theta = np.arccos(np.clip(tempTheta, -1, 1)) # In radians

                    intANUBIS = cav.intersectANUBISstationsShaft(theta, phi, ANUBISstations, position=[X,Y,Z], verbose=False)

                    if ( inShaft and not inATLAS and (len(intANUBIS[1]) >= 2) ):
                        passedHits.append((X,Y,Z))
                    else:
                        #print(inShaft, inATLAS, len(intANUBIS[1])) 
                        failedHits.append((X,Y,Z))
                    nHits+=1

        hitEnd3=datetime.datetime.now()
        print(hitEnd3)
        print(f"Took {hitEnd3 - hitStart3}")
        print(f"Passed: {len(passedHits)} ({len(passedHits)/(len(passedHits)+len(failedHits))}) |" 
               f"Failed: {len(failedHits)} ({len(failedHits)/(len(passedHits)+len(failedHits))})")

        print("plotting...")
        cav.plotFullCavern(shaftAnubisRPCs=ANUBISstations, plotATLAS=True, plotAcceptance=True, plotFailed=False, 
                           plotRPCs={"xy": True, "xz": True, "zy": True, "3D": False},
                           hits={"passed": passedHits, "failed": failedHits, "bins": hitBins}, suffix=f"_ShaftWithHits{args.suffix}")
        print(datetime.datetime.now())


    def getANUBISstationsDict(self):
        """
        Retourne un dictionnaire décrivant les stations ANUBIS dans un format
        exploitable par les fonctions d'intersection legacy :
        - Cas 'simple ceiling' (createSimpleRPCs) : dict avec clés 'r','theta','phi'
        - Cas 'shaft' (createShaftRPCs) : dict avec clés 'x','y','z','RPCradius','pipeCutoff'
        - Cas 'full ceiling' (ANUBIS_RPC_positions) : liste -> convertie via convertRPCList()
        """
        rp = getattr(self, "ANUBIS_RPCs", None)
        if rp is None:
            raise RuntimeError(
                "ANUBIS stations non initialisées. "
                "Appelle createSimpleRPCs() ou createShaftRPCs() avant d'interroger la géométrie."
            )

        # Déjà au bon format (simple ceiling)
        if isinstance(rp, dict) and ("r" in rp and "theta" in rp and "phi" in rp):
            return rp

        # Déjà au bon format (shaft)
        if isinstance(rp, dict) and ("x" in rp and "y" in rp and "z" in rp and "RPCradius" in rp):
            return rp

        # Cas "full ceiling" : liste d’objets → convertis en dict “corners/midPoint/plane/...”
        if isinstance(rp, list):
            return self.convertRPCList(rp)

        # Fallback défensif
        return rp