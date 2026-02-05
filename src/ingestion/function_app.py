import azure.functions as func
import logging
import json
from indexer import Indexer

app = func.FunctionApp()

@app.event_grid_trigger(arg_name="event")
def IngestBlob(event: func.EventGridEvent):
    logging.info('Python EventGrid trigger processed an event.')
    
    data = event.get_json()
    # Check if this is a Blob Created event
    # Event Grid schema for Storage: data['url'] is the blob url
    event_type = event.event_type
    
    if event_type == "Microsoft.Storage.BlobCreated":
        blob_url = data['url']
        logging.info(f"Blob Created: {blob_url}")
        
        try:
            indexer = Indexer()
            indexer.process_blob(blob_url)
        except Exception as e:
            logging.error(f"Error processing blob: {e}")
            raise
    else:
        logging.info(f"Skipping event type: {event_type}")
