import sys, slicer, numpy, os
# By Colin McCurdy and Mohamed Moselhy

# use an external file to convert a dicom volume to nrrd format
# input from the system should be the directory containing all of the dicom volumes you wish to convert (?)
topFolder = sys.argv[1]
vols = []

# load all volumes within the top folder into a set
for dirName, subdirList, fileList in os.walk(topFolder):
	for fname in fileList:
		if ".nrrd" in fname:
			volNode = slicer.util.loadVolume(os.path.join(dirName, fname), returnNode = True)[1]
			vols.append(volNode)
			
logging.error(str(len(vols)))

# startup segmentEditor to grow seeds and any additional effects
segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()

# for each volume we will perform the segmentation
# much of this code is based off of https://subversion.assembla.com/svn/slicerrt/trunk/SlicerRt/samples/PythonScripts/SegmentGrowCut/SegmentGrowCutSimple.py
for volNum, vol in enumerate(vols):
	# since there is an error, no point in looping through everything.
	if volNum == 2:
		break
	# setting up seg node
	masterVolumeNode = vol
	segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
	segmentationNode.SetName(vol.GetName())
	segmentationNode.CreateDefaultDisplayNodes()
	segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

	# create segment seed(s) for phantom volume
	volSeedPositions = ([50.5,24.9,32.4], [-50.5,24.9,32.4],[-50.5,24.9,-62.4]) # change these based on phantom location in image
	append = vtk.vtkAppendPolyData()
	for volSeedPosition in volSeedPositions:
		# create a seed as a sphere
		volSeed = vtk.vtkSphereSource()
		volSeed.SetCenter(volSeedPosition) 
		volSeed.SetRadius(10) # change this based on size of phantom or preference
		volSeed.Update()
		append.AddInputData(volSeed.GetOutput())

	append.Update()
	
	# add segmentation to the segmentationNode. "PhantomVolume" can be any string, and the following double array is colour.
	volSegID = segmentationNode.AddSegmentFromClosedSurfaceRepresentation(append.GetOutput(), "PhantomVolume", [1.0,0.0,0.0])

	# create segment seed(s) for the background noise
	bgSeedPositions = ([47,124,8],[-47,-80,8],[44,-90,32], [63,-83,6], [-68,106,-56]) # change these based on where the background/noise is in your image
	appendBg = vtk.vtkAppendPolyData()
	for bgSeedPos in bgSeedPositions:
		bgSeed = vtk.vtkSphereSource()
		bgSeed.SetCenter(bgSeedPos) 
		bgSeed.SetRadius(10)# change this based on background size
		bgSeed.Update()
		appendBg.AddInputData(bgSeed.GetOutput())

	appendBg.Update()
	
	# add background segmentation to the segmentationNode. Change the name or colour inputs based on preference.
	segmentationNode.AddSegmentFromClosedSurfaceRepresentation(appendBg.GetOutput(), "Background", [0.0,1.0,0.0])

	# create segmentation seed(s) for any additional feature that you wish to segment out
	featSeedPositions = ([32, -35, -11],[-28,-35,11],[-50,-35,11],[-15,42,18],[-15,30,18]) # change this based on the location of feature(s)
	appendFeat = vtk.vtkAppendPolyData()
	for featSeedPos in featSeedPositions:
		featSeed = vtk.vtkSphereSource()
		featSeed.SetCenter(featSeedPos) 
		featSeed.SetRadius(2) # small sphere for small features. Change depending on size of objects in your phantom
		featSeed.Update()
		appendFeat.AddInputData(featSeed.GetOutput())

	appendFeat.Update()
	
	# add feature segmentation seeds to the segmentationNode. Change the name or colour based on preference.
	segmentationNode.AddSegmentFromClosedSurfaceRepresentation(appendFeat.GetOutput(), "Feature", [0.0,0.0,1.0])
	
	# segmentEditorWidget.show() # this is for debugging if you need to!
	
	slicer.app.processEvents()
	segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
	segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
	slicer.mrmlScene.AddNode(segmentEditorNode)
	segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
	segmentEditorWidget.setSegmentationNode(segmentationNode)
	segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)
	
	# grow from seeds
	segmentEditorWidget.setActiveEffectByName("Grow from seeds")
	effect = segmentEditorWidget.activeEffect()
	effect.self().onPreview()
	
	# for troubleshooting / editing the seed growth, stop before the onApply() function
	effect.self().onApply()

	# grow the background further into the phantom volume segmentation
	# i needed this as my images had a noisy edge to the phantom volume, so it picked up to much noise as phantom volume
	segmentEditorWidget.setActiveEffectByName("Margin")
	mEffect = segmentEditorWidget.activeEffect()
	segmentEditorWidget.setCurrentSegmentID('Background') # change this based on your needs: does a segment not get all of your volume, or too much?
	mEffect.setParameter('MarginSizeMm', 8.0) # change 8.0 based on how well your segmentation performed. Change to negative if you need to shrink instead of grow.
	mEffect.self().onApply()
	
	# cleanup segment editor node
	slicer.mrmlScene.RemoveNode(segmentEditorNode)

# TODO below.
	
# analyze
# data = arrayFromVolume(masterVolumeNode)


# # Analyze Phantom Volume
# volSeg = segmentationNode.GetSegmentation().GetSegment('PhantomVolume')
# volSegMap = segmentationNode.GetBinaryLabelmapRepresentation('PhantomVolume')

# setup 
# thresh = vtk.vtkImageThreshold()
# thresh.setInputData(volSegMap)
# thresh.ThresholdByLower(0)
# thresh.SetInValue(0)
# thresh.SetOutValue(1)
# thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
# thresh.Update()

# # Use binary labelmap as a stencil
# stencil = vtk.vtkImageToImageStencil()
# stencil.SetInputData(thresh.GetOutput())
# stencil.ThresholdByUpper(1)
# stencil.Update()

# stat = vtk.vtkImageAccumulate()
# stat.SetInputData(masterVolumeNode.GetImageData())
# stat.SetStencilData(stencil.GetOutput())
# stat.Update()

# volSD = stat.GetStandardDeviation()[0]
# volMean = stat.GetMean()[0]

# volBinLabelMap = segmentationNode.GetBinaryLabelmapRepresentation('PhantomVolume')
# # setup binary mask
# volMask = arrayFromVolume(volBinLabelMap)
# # apply the mask to the DICOM array
# volMaskedData = volMask * data
# # use the numpy 'masked array' to get a masked array with the data above zero
# # note that this *could* remove data that would be zero in the segmentation, but that is unlikely
# volCompressedData = numpy.ma.masked_where(volMaskedData > 0, volMaskedData)
# volStdev = numpy.std(volCompressedData)
# volMean = numpy.mean(volCompressedData)

# # save in textfile
# numpy.savetxt("D:\generatedFiles\test.csv", volCompressedData, delimiter=',')

# # Analyze Features
# featBinLabelMap = segmentationNode.GetBinaryLabelmapRepresentation('Feature')
# # setup binary mask
# featMask = array(featBinLabelMap)
# # apply the mask to the DICOM array
# featMaskedData = featMask * data
# # use the numpy 'masked array' to get a masked array with the data above zero
# # note that this *could* remove data that would be zero in the segmentation, but that is unlikely
# featCompressedData = numpy.ma.masked_where(featMaskedData > 0, featMaskedData)
# featStdev = numpy.std(featCompressedData)
# featMean = numpy.mean(featCompressedData)

