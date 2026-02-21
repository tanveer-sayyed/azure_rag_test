import azure.functions as func
import logging
import json
from indexer import DocumentIndexer

app = func.FunctionApp()
document_indexer = DocumentIndexer()

@app.event_grid_trigger(arg_name="event")
def IngestBlob(event: func.EventGridEvent):
    """Handle Blob Created events from Event Grid to trigger indexing."""
    logging.info('Python EventGrid trigger processed an event.')

    event_data_json = event.get_json()
    event_type_string = event.event_type

    if event_type_string == "Microsoft.Storage.BlobCreated":
        blob_resource_url = event_data_json['url']
        logging.info(f"Blob Created: {blob_resource_url}")

        try:
            document_indexer.process_blob_document(blob_resource_url)
        except Exception as processing_error:
            logging.error(f"Error processing blob: {processing_error}")
            raise
    else:
        logging.info(f"Skipping event type: {event_type_string}")
