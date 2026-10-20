title Dashboard Data Communicator

start "" ..\HelperMethods\ClearTemp.bat "tmsMetaInfo.data,object_metadata.xml,metadata__exporter.log" 60
uvicorn API:app --host 0.0.0.0 --port 8000