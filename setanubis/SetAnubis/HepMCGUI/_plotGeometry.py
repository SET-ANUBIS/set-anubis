import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt 
import numpy as np

# Define a set of helper plotting functions for the ATLASCavern class

def plotCavernXY(self, ax, plotATLAS=False, plotAcceptance=False): 
    # Get the Cavern ceiling data grid
    cavernArch = self.createCavernVault(doPlot=False)

    # Cavern Boundaries
    ax.plot([self.CavernX[0], self.CavernX[0]], [self.CavernY[0], self.CavernY[1]], c=self.cavernColour, ls=self.cavernLS) #Left Vertical
    ax.plot([self.CavernX[1], self.CavernX[1]], [self.CavernY[0], self.CavernY[1]], c=self.cavernColour, ls=self.cavernLS) #Right Vertical
    #ax.plot([self.CavernX[0], self.CavernX[1]], [self.CavernY[0], self.CavernY[0]], c=self.cavernColour, ls=self.cavernLS) #Horizontal
    ax.plot([self.CavernTrench["X"][0], self.CavernTrench["X"][0]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][1]], 
            c=self.cavernColour, ls=self.cavernLS) #Left Vertical Trench 
    ax.plot([self.CavernTrench["X"][1], self.CavernTrench["X"][1]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][1]], 
            c=self.cavernColour, ls=self.cavernLS) #Right Vertical Trench 
    ax.plot([self.CavernTrench["X"][0], self.CavernTrench["X"][1]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][0]], 
            c=self.cavernColour, ls=self.cavernLS) #Horizontal Trench 

    # Add Hatched rectangles to make the cavern boundaries rectangular as a whole
    ax.add_patch(plt.Rectangle([self.CavernX[0], self.CavernTrench["Y"][0]], abs(self.CavernX[0]-self.CavernTrench["X"][0]), 
                              abs(self.CavernY[0]-self.CavernTrench["Y"][0]), fill=False, ec=self.cavernColour, fc=self.cavernColour, ls=self.cavernLS, hatch="//"))
    ax.add_patch(plt.Rectangle([self.CavernTrench["X"][1], self.CavernTrench["Y"][0]], abs(self.CavernX[1]-self.CavernTrench["X"][1]), 
                              abs(self.CavernY[0]-self.CavernTrench["Y"][0]), fill=False, ec=self.cavernColour, fc=self.cavernColour, ls=self.cavernLS, hatch="//"))

    if self.additionalAnnotation:
        ax.annotate("Cavern", (self.CavernX[0]+self.pointMargin,self.CavernTrench["Y"][0]-self.pointMargin), 
                    fontsize=self.annotationSize, ha="left", va="top")


    # Cavern Ceiling
    ax.plot(cavernArch["x"], cavernArch["y"], c=self.cavernColour, ls=self.cavernLS)
    # Access Shafts
    ax.plot([self.PX14_Centre["x"]-self.PX14_Radius,self.PX14_Centre["x"]-self.PX14_Radius], 
                              [self.PX14_LowestY, self.PX14_Centre["y"]+self.PX14_Height], ls=self.shaftLS["PX14"], c=self.shaftColour["PX14"], label="PX14", alpha=0.5)
    ax.plot([self.PX14_Centre["x"]+self.PX14_Radius,self.PX14_Centre["x"]+self.PX14_Radius], 
                              [self.PX14_LowestY, self.PX14_Centre["y"]+self.PX14_Height], ls=self.shaftLS["PX14"],c=self.shaftColour["PX14"], label="PX14", alpha=0.5)

    ax.plot([self.PX16_Centre["x"]-self.PX16_Radius,self.PX16_Centre["x"]-self.PX16_Radius],
                              [self.PX16_LowestY, self.PX16_Centre["y"]+self.PX16_Height], ls=self.shaftLS["PX16"],c=self.shaftColour["PX16"], label="PX16", alpha=0.5)
    ax.plot([self.PX16_Centre["x"]+self.PX16_Radius,self.PX16_Centre["x"]+self.PX16_Radius],
                              [self.PX16_LowestY, self.PX16_Centre["y"]+self.PX16_Height], ls=self.shaftLS["PX16"],c=self.shaftColour["PX16"], label="PX16", alpha=0.5)

    if self.additionalAnnotation:
        ax.annotate("PX14", (self.PX14_Centre["x"]+self.PX14_Radius+self.pointMargin, self.PX14_Centre["y"]+0.05*self.PX14_Height), 
                    fontsize=self.annotationSize, ha="left", va="bottom")
        ax.annotate("PX16", (self.PX16_Centre["x"]-(0.6*self.PX16_Radius)-self.pointMargin, self.PX16_Centre["y"]+0.05*self.PX16_Height), 
                    fontsize=self.annotationSize, ha="right", va="bottom")

    # Mark the Cavern Centre, IP, and Centre of Curvature for the ceiling
    if self.includeCavernCentreText:
        ax.scatter(0, 0, c="r", marker = "x", label="Cavern Centre")
        ax.annotate("Centre", (0+self.pointMargin,0-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    ax.scatter(self.IP["x"], self.IP["y"], c=self.ATLAScolour, marker = "o", label="IP")
    ax.annotate("IP", (self.IP["x"]+self.pointMargin, self.IP["y"]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    if self.includeCoCText:
        ax.scatter(self.centreOfCurvature["x"], self.centreOfCurvature["y"], c="b", marker = "D", label="Ceiling Centre of Curvature")
        ax.annotate("Centre of Curvature (Ceiling)", (self.centreOfCurvature["x"]+self.pointMargin, self.centreOfCurvature["y"]-self.pointMargin), 
                    fontsize=self.annotationSize, ha="left", va="top")

    if plotATLAS:
       ax.add_patch( plt.Circle((self.ATLAS_Centre["x"], self.ATLAS_Centre["y"]), self.radiusATLAS, color=self.ATLAScolour, fill=False, ls=self.ATLASls) )
       if self.includeATLASlimit:
           ax.add_patch( plt.Circle((self.ATLAS_Centre["x"], self.ATLAS_Centre["y"]), self.radiusATLAStracking, color=self.ATLAScolour, fill=False, ls='dotted') )
       if self.additionalAnnotation:
            ax.annotate("ATLAS", (self.ATLAS_Centre["x"], self.ATLAS_Centre["y"]+self.radiusATLAS+self.pointMargin), 
                        fontsize=self.annotationSize, ha="center", va="bottom")

    if plotAcceptance:
        # Plot a rough impression of the Acceptance
        ax.plot([self.IP["x"], self.CavernX[0]], [self.IP["y"], self.CavernY[1]], c="k", alpha=0.25, linestyle="--")
        ax.plot([self.IP["x"], self.CavernX[1]], [self.IP["y"], self.CavernY[1]], c="k", alpha=0.25, linestyle="--")

    ax.set_xlim(-18,18)
    ax.set_ylim(-18,25)

def plotCavernXZ(self, ax, plotATLAS=False): 
    # Cavern Boundaries
    ax.plot( [self.CavernX[0], self.CavernX[1]], [self.CavernZ[0], self.CavernZ[0]], c=self.cavernColour, ls=self.cavernLS)
    ax.plot( [self.CavernX[0], self.CavernX[1]], [self.CavernZ[1], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS)
    ax.plot( [self.CavernX[0], self.CavernX[0]], [self.CavernZ[0], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS)
    ax.plot( [self.CavernX[1], self.CavernX[1]], [self.CavernZ[0], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS)
    if self.additionalAnnotation:
        ax.annotate("Cavern", (self.CavernX[0]+self.pointMargin, self.CavernZ[0]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")

    # Access Shafts
    ax.add_patch( plt.Circle((self.PX14_Centre["x"], self.PX14_Centre["z"]), self.PX14_Radius, color=self.shaftColour["PX14"], fill=False, ls=self.shaftLS["PX14"]) )
    ax.add_patch( plt.Circle((self.PX16_Centre["x"], self.PX16_Centre["z"]), self.PX16_Radius, color=self.shaftColour["PX16"], fill=False, ls=self.shaftLS["PX16"]) )
    if self.additionalAnnotation:
        ax.annotate("PX14", (self.PX14_Centre["x"], self.PX14_Centre["z"]+self.PX14_Radius+self.pointMargin), fontsize=self.annotationSize, ha="center", va="bottom")
        ax.annotate("PX16", (self.PX16_Centre["x"], self.PX16_Centre["z"]-self.PX16_Radius-self.pointMargin), fontsize=self.annotationSize, ha="center", va="top")
    
    # Mark the Cavern Centre, IP, and Centre of Curvature for the ceiling
    if self.includeCavernCentreText:
        ax.scatter(0, 0, c="r", marker = "x", label="Cavern Centre")
        ax.annotate("Centre", (0+self.pointMargin,0-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    ax.scatter(self.IP["x"], self.IP["z"], c=self.ATLAScolour, marker = "o", label="IP")
    ax.annotate("IP", (self.IP["x"]+self.pointMargin, self.IP["z"]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    if self.includeCoCText:
        ax.plot([self.centreOfCurvature["x"]]*2, [self.CavernZ[0], self.CavernZ[1]], c="b", linestyle="--", label="Ceiling Centre of Curvature")
        ax.annotate("Centre of Curvature (Ceiling)", (self.centreOfCurvature["x"]+self.pointMargin,self.CavernZ[0]/4), 
                    fontsize=self.annotationSize, ha="left", va="top")

    if plotATLAS:
        ax.plot( [self.ATLAS_Centre["x"]-self.radiusATLAS,self.ATLAS_Centre["x"]+self.radiusATLAS], [self.ATLAS_Z[0],self.ATLAS_Z[0]], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Centre["x"]-self.radiusATLAS,self.ATLAS_Centre["x"]-self.radiusATLAS], [self.ATLAS_Z[0],self.ATLAS_Z[1]], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Centre["x"]-self.radiusATLAS,self.ATLAS_Centre["x"]+self.radiusATLAS], [self.ATLAS_Z[1],self.ATLAS_Z[1]], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Centre["x"]+self.radiusATLAS,self.ATLAS_Centre["x"]+self.radiusATLAS], [self.ATLAS_Z[0],self.ATLAS_Z[1]], c=self.ATLAScolour, ls=self.ATLASls)
        if self.additionalAnnotation:
            ax.annotate("ATLAS", (self.ATLAS_Centre["x"]-self.radiusATLAS+self.pointMargin, self.ATLAS_Z[0]+self.pointMargin), 
                        fontsize=self.annotationSize, ha="left", va="bottom")


    ax.set_xlim(-18,18)
    ax.set_ylim(-30,30)

def plotCavernZY(self, ax, plotATLAS=False, plotAcceptance=False): 
    # Cavern Boundaries
    if self.includeCavernYinZY:
        ax.plot([self.CavernZ[0], self.CavernZ[1]], [self.CavernY[1], self.CavernY[1]], c=self.cavernColour, ls="--")

    ax.plot([self.CavernZ[0], self.CavernZ[0]], [self.CavernY[0], self.archRadius+self.centreOfCurvature["y"]], c=self.cavernColour, ls=self.cavernLS)
    ax.plot([self.CavernZ[1], self.CavernZ[1]], [self.CavernY[0], self.archRadius+self.centreOfCurvature["y"]], c=self.cavernColour, ls=self.cavernLS)
    #ax.plot([self.CavernZ[0], self.CavernZ[1]], [self.CavernY[0], self.CavernY[0]], c=self.cavernColour, ls=self.cavernLS)
    # Cavern Ceiling
    ax.plot([self.CavernZ[0], self.CavernZ[1]], [self.archRadius+self.centreOfCurvature["y"], self.archRadius+self.centreOfCurvature["y"]], 
                              c=self.cavernColour, ls=self.cavernLS)

    ax.plot([self.CavernTrench["Z"][0], self.CavernTrench["Z"][0]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][1]], 
            c=self.cavernColour, ls=self.cavernLS) #Left Vertical Trench 
    ax.plot([self.CavernTrench["Z"][1], self.CavernTrench["Z"][1]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][1]], 
            c=self.cavernColour, ls=self.cavernLS) #Right Vertical Trench 
    ax.plot([self.CavernTrench["Z"][0], self.CavernTrench["Z"][1]], [self.CavernTrench["Y"][0],self.CavernTrench["Y"][0]], 
            c=self.cavernColour, ls=self.cavernLS) #Horizontal Trench 


    # Add Hatched rectangles to make the cavern boundaries rectangular as a whole
    ax.add_patch(plt.Rectangle([self.CavernZ[0], self.CavernTrench["Y"][0]], abs(self.CavernZ[0]-self.CavernTrench["Z"][0]),  
                            abs(self.CavernY[0]-self.CavernTrench["Y"][0]), fill=False, ec=self.cavernColour, fc=self.cavernColour, ls=self.cavernLS,hatch="//"))
    ax.add_patch(plt.Rectangle([self.CavernTrench["Z"][1], self.CavernTrench["Y"][0]], abs(self.CavernZ[1]-self.CavernTrench["Z"][1]),  
                              abs(self.CavernY[0]-self.CavernTrench["Y"][0]), fill=False, ec=self.cavernColour, fc=self.cavernColour, ls=self.cavernLS,hatch="//"))

    if self.additionalAnnotation:
        ax.annotate("Cavern", (self.CavernZ[0]+self.pointMargin, self.CavernTrench["Y"][0]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")

    # Access Shafts
    ax.plot([self.PX14_Centre["z"]-self.PX14_Radius, self.PX14_Centre["z"]-self.PX14_Radius],
            [self.PX14_Centre["y"], self.PX14_Centre["y"]+self.PX14_Height], c=self.shaftColour["PX14"], ls=self.shaftLS["PX14"], label="PX14", alpha=0.5)
    ax.plot([self.PX14_Centre["z"]+self.PX14_Radius,self.PX14_Centre["z"]+self.PX14_Radius],
            [self.PX14_Centre["y"], self.PX14_Centre["y"]+self.PX14_Height], c=self.shaftColour["PX14"], ls=self.shaftLS["PX14"], label="PX14", alpha=0.5)
    ax.plot([self.PX16_Centre["z"]-self.PX16_Radius,self.PX16_Centre["z"]-self.PX16_Radius],
            [self.PX16_Centre["y"], self.PX16_Centre["y"]+self.PX16_Height], c=self.shaftColour["PX16"], ls=self.shaftLS["PX16"], label="PX16", alpha=0.5)
    ax.plot([self.PX16_Centre["z"]+self.PX16_Radius,self.PX16_Centre["z"]+self.PX16_Radius],
            [self.PX16_Centre["y"], self.PX16_Centre["y"]+self.PX16_Height], c=self.shaftColour["PX16"], ls=self.shaftLS["PX16"], label="PX16", alpha=0.5)

    if self.additionalAnnotation:
        ax.annotate("PX14", (self.PX14_Centre["z"]+self.PX14_Radius+self.pointMargin, self.PX14_Centre["y"]+0.05*self.PX14_Height), 
                    fontsize=self.annotationSize, ha="left", va="bottom")
        ax.annotate("PX16", (self.PX16_Centre["z"]-self.PX16_Radius-self.pointMargin, self.PX16_Centre["y"]+0.05*self.PX16_Height), 
                    fontsize=self.annotationSize, ha="right", va="bottom")

    # Mark the Cavern Centre, IP, and Centre of Curvature for the ceiling
    if self.includeCavernCentreText:
        ax.scatter(0, 0, c="r", marker = "x", label="Cavern Centre")
        ax.annotate("Centre", (0+self.pointMargin,0-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    ax.scatter(self.IP["z"], self.IP["y"], c=self.ATLAScolour, marker = "o", label="IP")
    ax.annotate("IP", (self.IP["z"]+self.pointMargin, self.IP["y"]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")
    if self.includeCoCText:
        ax.plot( [self.CavernZ[0], self.CavernZ[1]], [self.centreOfCurvature["y"]]*2, c="b", linestyle="--", label="Ceiling Centre of Curvature")
        ax.annotate("Centre of Curvature (Ceiling)", ((self.CavernZ[0]/2)+self.pointMargin, self.centreOfCurvature["y"]-self.pointMargin), 
                    fontsize=self.annotationSize, ha="left", va="top")

    if plotATLAS:
        ax.plot( [self.ATLAS_Z[0],self.ATLAS_Z[0]], [self.ATLAS_Centre["y"]-self.radiusATLAS,self.ATLAS_Centre["y"]+self.radiusATLAS], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Z[0],self.ATLAS_Z[1]], [self.ATLAS_Centre["y"]-self.radiusATLAS,self.ATLAS_Centre["y"]-self.radiusATLAS], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Z[1],self.ATLAS_Z[1]], [self.ATLAS_Centre["y"]-self.radiusATLAS,self.ATLAS_Centre["y"]+self.radiusATLAS], c=self.ATLAScolour, ls=self.ATLASls)
        ax.plot( [self.ATLAS_Z[0],self.ATLAS_Z[1]], [self.ATLAS_Centre["y"]+self.radiusATLAS,self.ATLAS_Centre["y"]+self.radiusATLAS], c=self.ATLAScolour, ls=self.ATLASls)
        if self.includeATLASlimit:
            ax.plot( [self.ATLAS_Z[0],self.ATLAS_Z[1]], [self.ATLAS_Centre["y"]-self.radiusATLAStracking,self.ATLAS_Centre["y"]-self.radiusATLAStracking], 
                     c=self.ATLAScolour, ls="dotted")
            ax.plot( [self.ATLAS_Z[0],self.ATLAS_Z[1]], [self.ATLAS_Centre["y"]+self.radiusATLAStracking,self.ATLAS_Centre["y"]+self.radiusATLAStracking],
                     c=self.ATLAScolour, ls="dotted")

        if self.additionalAnnotation:
            ax.annotate("ATLAS", (self.ATLAS_Z[0]+self.pointMargin, self.ATLAS_Centre["y"]-self.radiusATLAS+self.pointMargin), 
                        fontsize=self.annotationSize, ha="left", va="bottom")

    if plotAcceptance:
        # Plot a rough impression of the Acceptance
        ax.plot([self.IP["z"], self.CavernZ[0]], [self.IP["y"], self.CavernY[1]], c="k", alpha=0.25, linestyle="--")
        ax.plot([self.IP["z"], self.CavernZ[1]], [self.IP["y"], self.CavernY[1]], c="k", alpha=0.25, linestyle="--")

    ax.set_xlim(-30,30)
    ax.set_ylim(-18,25)

def plotCavern3D(self, ax, plotATLAS=False, plotAcceptance=False): 
    # Get the Cavern ceiling data grid
    cavernArch = self.createCavernVault(doPlot=False)
    # Get the Access Shafts data grid 
    accessShafts = self.createAccessShafts()
    # Cavern Boundaries
    cavernBounds = { "x": np.linspace(self.CavernX[0], self.CavernX[1],100),
                     "y": np.linspace(self.CavernY[0], self.CavernY[1],100),
                     "z": np.linspace(self.CavernZ[0], self.CavernZ[1],100),}

    #3D Plot
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    # Cavern Boundaries
    cavX_Y, cavY_X = np.meshgrid(cavernBounds["x"], cavernBounds["y"])
    cavY_Z, cavZ_Y = np.meshgrid(cavernBounds["y"], cavernBounds["z"])
    cavX_Z, cavZ_X = np.meshgrid(cavernBounds["x"], cavernBounds["z"])
    # XY Faces
    ax.plot_surface(cavX_Y, self.CavernZ[0]*np.ones(cavX_Y.shape), cavY_X, rstride=4, cstride=4, alpha=0.25)
    ax.plot_surface(cavX_Y, self.CavernZ[1]*np.ones(cavX_Y.shape), cavY_X, rstride=4, cstride=4, alpha=0.25)
    # YZ Faces
    ax.plot_surface(self.CavernX[0]*np.ones(cavY_Z.shape), cavZ_Y, cavY_Z, rstride=4, cstride=4, alpha=0.25)
    ax.plot_surface(self.CavernX[1]*np.ones(cavY_Z.shape), cavZ_Y, cavY_Z, rstride=4, cstride=4, alpha=0.25)
    # XZ Face
    ax.plot_surface(cavX_Z, cavZ_X, self.CavernY[0]*np.ones(cavX_Z.shape), rstride=4, cstride=4, alpha=0.25)
    # IP
    ax.scatter([self.IP["x"]], [self.IP["z"]], [self.IP["y"]], c="g", marker = "o", label="IP") 

    # Access Shafts
    for shaft in ["PX14", "PX16"]:
        ax.plot_surface(accessShafts[shaft]["x"], accessShafts[shaft]["z"], accessShafts[shaft]["y"], rstride=4, cstride=4, alpha=0.25, label=shaft)

    # Ceiling
    xx, zz = np.meshgrid(cavernArch["x"], cavernArch["z"])

    mask = np.logical_and(np.sqrt((xx-self.PX14_Centre["x"])**2 + (zz-self.PX14_Centre["z"])**2) > self.PX14_Radius, 
                            np.sqrt((xx-self.PX16_Centre["x"])**2 + (zz-self.PX16_Centre["z"])**2) > self.PX16_Radius)

    xx[~mask] = np.nan
    zz[~mask] = np.nan
    yy = np.sqrt(np.power(self.archRadius,2) - np.power(xx-self.centreOfCurvature["x"],2)) + self.centreOfCurvature["y"]

    ax.plot_surface(xx, zz, yy, rstride=4, cstride=4, alpha=0.25)

    if plotATLAS:
        atlasX =  np.linspace(self.ATLAS_Centre["x"]-self.radiusATLAS,self.ATLAS_Centre["x"]+self.radiusATLAS, 100)
        atlasZ =  np.linspace(self.ATLAS_Z[0], self.ATLAS_Z[1], 100)
        
        atlasXX, atlasZZ = np.meshgrid(atlasX, atlasZ)
        atlasYY = np.sqrt(np.power(self.radiusATLAS,2) - np.power(atlasXX-self.ATLAS_Centre["x"],2))
        ax.plot_surface(atlasXX, atlasZZ, atlasYY + self.ATLAS_Centre["y"], rstride=4, cstride=4, alpha=0.4, color="gray")
        ax.plot_surface(atlasXX, atlasZZ, -atlasYY + self.ATLAS_Centre["y"], rstride=4, cstride=4, alpha=0.4, color="gray")

    if plotAcceptance:
        # Plot a rough impression of the Acceptance
        ax.plot([self.IP["x"], self.CavernX[0]], [self.IP["z"], self.CavernZ[0]], [self.IP["y"],self.obtainCavernYFromX(self.CavernX[0])], 
                 c="k", alpha=0.25, linestyle="--")
        ax.plot([self.IP["x"], self.CavernX[0]], [self.IP["z"], self.CavernZ[1]], [self.IP["y"],self.obtainCavernYFromX(self.CavernX[0])], 
                 c="k", alpha=0.25, linestyle="--")
        ax.plot([self.IP["x"], self.CavernX[1]], [self.IP["z"], self.CavernZ[0]], [self.IP["y"], self.obtainCavernYFromX(self.CavernX[1])], 
                c="k", alpha=0.25, linestyle="--")
        ax.plot([self.IP["x"], self.CavernX[1]], [self.IP["z"], self.CavernZ[1]], [self.IP["y"],self.obtainCavernYFromX(self.CavernX[1])], 
                c="k", alpha=0.25, linestyle="--")

    ax.set_zlabel("y /m")
    ax.set_xlim(-30,30)
    ax.set_ylim(-30,30)
    ax.set_zlim(-30,30)

def plotCavernCeilingCoords(self, ax):
    ax.plot([-self.arcLength/2, -self.arcLength/2], [self.CavernZ[0], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS) 
    ax.plot([ self.arcLength/2,  self.arcLength/2], [self.CavernZ[0], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS) 
    ax.plot([-self.arcLength/2,  self.arcLength/2], [self.CavernZ[0], self.CavernZ[0]], c=self.cavernColour, ls=self.cavernLS) 
    ax.plot([-self.arcLength/2,  self.arcLength/2], [self.CavernZ[1], self.CavernZ[1]], c=self.cavernColour, ls=self.cavernLS) 

    if self.additionalAnnotation:
        ax.annotate("Cavern", ((-self.arcLength/2)+self.pointMargin, self.CavernZ[0]-self.pointMargin), fontsize=self.annotationSize, ha="left", va="top")

    # Plot the unrolled Shafts for reference
    for shaft, shaftParams in self.shaftParams.items():
        shaftX = np.linspace(shaftParams["Centre"]["x"]-shaftParams["radius"], shaftParams["Centre"]["x"]+shaftParams["radius"],100)
        # For each X get ~2 Z values -- treat as LocalZ.
        shaftZ1 =  np.sqrt(np.power(shaftParams["radius"],2) - np.power(shaftX,2)) + shaftParams["Centre"]["z"]
        shaftZ2 = -np.sqrt(np.power(shaftParams["radius"],2) - np.power(shaftX,2)) + shaftParams["Centre"]["z"]

        # Convert each X value into local coordinates.
        heights = self.obtainCavernYFromX(shaftX) - self.centreOfCurvature["y"]
        localShaftX = self.archRadius*np.arctan2(shaftX, heights)

        ax.plot(localShaftX, shaftZ1, c=self.shaftColour[shaft], ls=self.shaftLS[shaft])
        ax.plot(localShaftX, shaftZ2, c=self.shaftColour[shaft], ls=self.shaftLS[shaft])

        if self.additionalAnnotation:
            ax.annotate(shaft, (shaftParams["Centre"]["x"], shaftParams["Centre"]["z"]+shaftParams["radius"]+self.pointMargin), 
                        fontsize=self.annotationSize, ha="center", va="bottom")

#---------------------------------------#
#- Set of functions to plot RPC Layers -#
#---------------------------------------#
# ANUBISrpcs is a list of RPClayers, each contain a list of RPCs in the format:
#   - "corners": 8 (x,y,z) coordinates corresponding to their corners,
#   - "midPoint": The midPoint of the RPC in (x,y,z), 
#   - "LayerID" and "RPCid": A Layer ID and RPC ID to uniquely identify the RPC
#   - "plane": A Sympy plane in the eta-phi plane that passes through the midpoint
def plotRPCsXY(self, ax, ANUBISrpcs):
    nLayer=0
    for rpcLayer in ANUBISrpcs:
        tempRPCList = self.convertRPCList(rpcLayer)
        initialZ = tempRPCList["corners"][0][0][2]
        # Plot midpoints
        ax.scatter([x[0] for x in tempRPCList["midPoint"]], [y[1] for y in tempRPCList["midPoint"]], c=self.LayerColours[nLayer], label=f"Layer {nLayer}")
        # Plot RPC Boundaries
        nInterations=0
        for i in range(len(tempRPCList["corners"])):
            c = tempRPCList["corners"][i]
            
            if c[0][2] != initialZ:
                continue
            nInterations+=1

            # For Front of RPC in z, use 1--3, 1--5, 3--7, 5--7 for back of RPC.
            ax.plot( [c[0][0], c[2][0]], [c[0][1],c[2][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[0][0], c[4][0]], [c[0][1],c[4][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[2][0], c[6][0]], [c[2][1],c[6][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[4][0], c[6][0]], [c[4][1],c[6][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
        nLayer+=1

def plotRPCsXZ(self, ax, ANUBISrpcs):
    nLayer=0
    for rpcLayer in ANUBISrpcs:
        if nLayer!=0:
            continue # For clarity only plot the first RPC layer
        tempRPCList = self.convertRPCList(rpcLayer)
        # Plot midpoints
        ax.scatter([x[0] for x in tempRPCList["midPoint"]], [z[2] for z in tempRPCList["midPoint"]], c=self.LayerColours[nLayer], label=f"Layer {nLayer}")
        # Plot RPC Boundaries
        for i in range(len(tempRPCList["corners"])):
            c = tempRPCList["corners"][i]
            # For the Top of the RPC: use 4--5, 5--7, 4--6 & 6--7 for Bottom of RPC.
            ax.plot( [c[0][0], c[1][0]], [c[0][2],c[1][2]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")

def plotRPCsZY(self, ax, ANUBISrpcs):
    nLayer=0
    for rpcLayer in ANUBISrpcs:
        if nLayer!=0:
            continue #Plot only the first layer for clarity
        tempRPCList = self.convertRPCList(rpcLayer)
        # Plot midpoints
        ax.scatter([z[2] for z in tempRPCList["midPoint"]], [y[1] for y in tempRPCList["midPoint"]], 
                    c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
        # Plot RPC Boundaries
        for i in range(len(tempRPCList["corners"])):
            c = tempRPCList["corners"][i]
            # For left x corner of the RPC: use 2--3, 2--6, 3--7 & 6--7 for Right of RPC.
            ax.plot( [c[0][2], c[1][2]], [c[0][1],c[1][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[0][2], c[4][2]], [c[0][1],c[4][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[1][2], c[5][2]], [c[1][1],c[5][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
            ax.plot( [c[4][2], c[5][2]], [c[4][1],c[5][1]], c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")
        nLayer+=1

def plotRPCs3D(self, ax, ANUBISrpcs):
    nLayer=0
    for rpcLayer in ANUBISrpcs:
        tempRPCList = self.convertRPCList(rpcLayer)
        # Plot midpoints
        ax.scatter([x[0] for x in tempRPCList["midPoint"]], [z[2] for z in tempRPCList["midPoint"]], [y[1] for y in tempRPCList["midPoint"]], 
                   c=self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}")

        # Plot RPC Boundaries
        for i in range(len(tempRPCList["corners"])):
            c = tempRPCList["corners"][i]
            # For left x corner of the RPC: use 2--3, 2--6, 3--7 & 6--7 for Right of RPC.
            ax.plot_surface(c[:][0], c[:][2], c[:][1], color = self.LayerColours[nLayer%len(self.LayerColours)], label=f"Layer {nLayer}", 
                            alpha=0.4, rstride=5, cstride=4)
        nLayer+=1

#----------------------------------------------#
#- Set of functions to plot Simple RPC Layers -#
#----------------------------------------------#
# Here ANUBISrpcs contain a radial distance and the angular coverage.
# This has the form of: RPCs={"r": [[minR, maxR],...], "theta": [[minTheta, maxTheta],...], "phi": [[minPhi, maxPhi],...]}
def plotSimpleRPCsXY(self, ax, ANUBISrpcs):
    for idx in range(len(ANUBISrpcs["r"])):
        ax.add_patch( matplotlib.patches.Arc((self.centreOfCurvature["x"], self.centreOfCurvature["y"]),
                                            width = 2*(ANUBISrpcs["r"][idx][0]), height = 2*(ANUBISrpcs["r"][idx][0]), 
                                            angle=0,
                                            theta1=min(ANUBISrpcs["phi"]["CoC"][idx])*(180/np.pi), theta2=max(ANUBISrpcs["phi"]["CoC"][idx])*(180/np.pi),
                                            color=self.LayerColours[idx%len(self.LayerColours)], fill=False, ls=self.LayerLS[idx%len(self.LayerLS)]) )
        ax.add_patch( matplotlib.patches.Arc((self.centreOfCurvature["x"], self.centreOfCurvature["y"]),
                                            width = 2*(ANUBISrpcs["r"][idx][1]), height = 2*(ANUBISrpcs["r"][idx][1]), 
                                            angle=0,
                                            theta1=min(ANUBISrpcs["phi"]["CoC"][idx])*(180/np.pi), theta2=max(ANUBISrpcs["phi"]["CoC"][idx])*(180/np.pi),
                                            color=self.LayerColours[idx%len(self.LayerColours)], fill=False, ls=self.LayerLS[idx%len(self.LayerLS)]) )

# Specify a set of stations to plot with stationIndices
def plotSimpleRPCsLocalCoords(self, ax, ANUBISrpcs, stationIndices=[]):
    for i in range(len(ANUBISrpcs["r"])):
        if len(stationIndices)!=0 and i not in stationIndices:
            continue

        # Get the total angle covered by the RPC layers for this station relative to Centre of Curvature
        stationAngleCoverage = abs(max(ANUBISrpcs["phi"]["CoC"][i]) - min(ANUBISrpcs["phi"]["CoC"][i])) 
        localXLength = ANUBISrpcs["r"][i][0] * stationAngleCoverage

        # Plot the unrolled RPC station 
        ax.plot([-localXLength/2, -localXLength/2], [self.CavernZ[0], self.CavernZ[1]],
                 c=self.LayerColours[i%len(self.LayerColours)], ls=self.LayerLS[i%len(self.LayerLS)])
        ax.plot([ localXLength/2,  localXLength/2], [self.CavernZ[0], self.CavernZ[1]], 
                 c=self.LayerColours[i%len(self.LayerColours)], ls=self.LayerLS[i%len(self.LayerLS)])
        ax.plot([-localXLength/2,  localXLength/2], [self.CavernZ[0], self.CavernZ[0]], 
                 c=self.LayerColours[i%len(self.LayerColours)], ls=self.LayerLS[i%len(self.LayerLS)])
        ax.plot([-localXLength/2,  localXLength/2], [self.CavernZ[1], self.CavernZ[1]],
                 c=self.LayerColours[i%len(self.LayerColours)], ls=self.LayerLS[i%len(self.LayerLS)])
        
#-----------------------------------------------#
#- Set of functions to plot RPCs in the shafts -#
#-----------------------------------------------#
# This has the form of: RPCs={"x": [] "y": [[minY,maxY]], "z": [], "RPCradius": [], "pipeCutoff": pipeCutoff}
# - Defining cylinders in "xz"
#-----------------------------------------------#
def shaftRPCshape(self,xOffset, zOffset, pipeCutoff, radius):
    x, z = [],[]
    for angle in np.linspace(0,360,100)*(np.pi/180):
        tempX = radius*np.sin(angle)
        tempZ = radius*np.cos(angle)

        if pipeCutoff["x"]!="" and ((tempX < pipeCutoff["x"] and pipeCutoff["x"]<0) or (tempX > pipeCutoff["x"] and pipeCutoff["x"]>0)):
            tempX = pipeCutoff["x"]

        if pipeCutoff["z"]!="" and ((tempZ < pipeCutoff["z"] and pipeCutoff["z"]<0) or (tempZ > pipeCutoff["z"] and pipeCutoff["z"]>0)):
            tempZ = pipeCutoff["z"]

        x.append(tempX + xOffset)
        z.append(tempZ + zOffset)

    return x, z

def plotShaftRPCsXY(self, ax, ANUBISrpcs):
    for idx in range(len(ANUBISrpcs["x"])):
        pltX, pltZ = self.shaftRPCshape(ANUBISrpcs["x"][idx], ANUBISrpcs["z"][idx], ANUBISrpcs["pipeCutoff"], ANUBISrpcs["RPCradius"][idx])
    
        ax.plot(pltX, [ANUBISrpcs["y"][idx][0]]*len(pltX), color=self.LayerColours[idx%len(self.LayerColours)], 
                ls=self.LayerLS[idx%len(self.LayerLS)], label=f"Layer {idx}")
        ax.plot(pltX, [ANUBISrpcs["y"][idx][1]]*len(pltX), color=self.LayerColours[idx%len(self.LayerColours)], 
                ls=self.LayerLS[idx%len(self.LayerLS)], label=f"_Layer {idx}")

def plotShaftRPCsZY(self, ax, ANUBISrpcs):
    for idx in range(len(ANUBISrpcs["x"])):
        pltX, pltZ = self.shaftRPCshape(ANUBISrpcs["x"][idx], ANUBISrpcs["z"][idx], ANUBISrpcs["pipeCutoff"], ANUBISrpcs["RPCradius"][idx])

        ax.plot(pltZ, [ANUBISrpcs["y"][idx][0]]*len(pltZ), color=self.LayerColours[idx%len(self.LayerColours)], 
                ls=self.LayerLS[idx%len(self.LayerLS)], label=f"Layer {idx}")
        ax.plot(pltZ, [ANUBISrpcs["y"][idx][1]]*len(pltZ), color=self.LayerColours[idx%len(self.LayerColours)],
                ls=self.LayerLS[idx%len(self.LayerLS)], label=f"_Layer {idx}")

def plotShaftRPCsXZ(self, ax, ANUBISrpcs, localCoords=False):
    for idx in range(len(ANUBISrpcs["x"])):
        #ax.add_patch( plt.Circle((ANUBISrpcs["x"][idx], ANUBISrpcs["z"][idx]), ANUBISrpcs["RPCradius"][idx], 
        #                          color=self.LayerColours[idx%len(self.LayerColours)], fill=False, ls=self.LayerLS[idx%len(self.LayerLS)]) )
        if localCoords:
            pltX, pltZ = self.shaftRPCshape(0, 0, ANUBISrpcs["pipeCutoff"], ANUBISrpcs["RPCradius"][idx])
        else:
            pltX, pltZ = self.shaftRPCshape(ANUBISrpcs["x"][idx], ANUBISrpcs["z"][idx], ANUBISrpcs["pipeCutoff"], ANUBISrpcs["RPCradius"][idx])

        ax.plot(pltX, pltZ, color=self.LayerColours[idx%len(self.LayerColours)], ls=self.LayerLS[idx%len(self.LayerLS)], label=f"Layer {idx}")

def plotShaftRPCs3D(self, ax, ANUBISrpcs):
    #TODO: Fix, Not working properly at the moment to display the shaft layers
    for idx in range(len(ANUBISrpcs["x"])):
        pltX, pltZ = self.shaftRPCshape(ANUBISrpcs["x"][idx], ANUBISrpcs["z"][idx], ANUBISrpcs["pipeCutoff"], ANUBISrpcs["RPCradius"][idx])
        pltY, theta = np.meshgrid(np.linspace(ANUBISrpcs["y"][idx][0], ANUBISrpcs["y"][idx][1], len(pltX)), np.linspace(0,360,len(pltX)))
    
        ax.plot_surface(pltX, pltZ, pltY, color = self.LayerColours[idx%len(self.LayerColours)], label=f"Layer {idx}", alpha=0.7, rstride=5, cstride=4)

#--------------------------------------------#
#-     Plot Hits as 2D or 3D histograms     -#
#--------------------------------------------#
def plotHitsHist(self, axis, hits, binDict={"rangeX": [-20,20], "rangeY": [-25,25], "nX": 80, "nY": 100}):
    counts, xedges, yedges, im = axis.hist2d(hits[0], hits[1], range=(binDict["rangeX"],binDict["rangeY"]), bins = (binDict["nX"], binDict["nY"]), cmin=1)
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04, ax=axis)

def plotHitsScatter(self, ax, hits, styleDict={"colour": "k", "marker": "."}):
    ax.scatter(hits[0], hits[1], c=styleDict["colour"], marker=styleDict["marker"])
