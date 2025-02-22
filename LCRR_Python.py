import arcpy
import os
import uuid
import zipfile
import datetime
import reportlab
import shutil
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileReader, PdfFileWriter

# Set the workspace 
working_folder = r'\\MNUSLAS2NPTCX02\Data\Analysis\LCRR\Postcards'
gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NWDWaterSystem_EDIT_AGOL.sde'

arcpy.env.workspace = str(gdb)
##use the fc/table in the map
wServices = arcpy.GetParameterAsText(0)
wMeters = gdb + str('\DBO.wMeters')
LCRR_Letter_Tracking = gdb + str('\DBO.LCRRLetterTracking')


# Get the current date
current_date = datetime.datetime.now().strftime("%Y-%m-%d")  # Formats the date as YYYY-MM-DD

template_pdf_path = f'{working_folder}\\Newport_SLM_Postcard.pdf'

# Construct the path to the folder within the working_folder
date_specific_folder = os.path.join(working_folder, current_date)
# Check if the folder exists, and if not, create it
if not os.path.exists(date_specific_folder):
    os.makedirs(date_specific_folder)
    arcpy.AddMessage(f"Created folder: {date_specific_folder}")


def add_multiline_address_to_pdf(template_pdf_path, output_pdf_path, address_lines, x_position=288, y_position=150, line_spacing=14):
    """
    Adds a multi-line address to a PDF.

    Parameters:
    - template_pdf_path: Path to the input PDF template.
    - output_pdf_path: Path where the modified PDF will be saved.
    - address_lines: A list of strings, each representing a line of the address.
    - x_position: The X coordinate for the start of the address.
    - y_position: The Y coordinate for the start of the address (bottom line).
    - line_spacing: The amount of space between each line of the address.
    """
    # Create a temporary PDF with the address
    address_pdf_path = f'{working_folder}\\temp_address_overlay.pdf'
    c = canvas.Canvas(address_pdf_path)
    
    # Draw each line of the address, adjusting the Y position for each line
    current_y_position = y_position
    for line in reversed(address_lines):  # Start from the bottom line if y_position is the bottom line
        c.drawString(x_position, current_y_position, line)
        current_y_position += line_spacing  # Move up for the next line
    
    c.save()

    # Merge the address overlay with the original PDF
    original = PdfFileReader(open(template_pdf_path, 'rb'))
    address_overlay = PdfFileReader(open(address_pdf_path, 'rb'))
    output_pdf = PdfFileWriter()

    # Assuming you're adding the address to the first page of the PDF
    page = original.getPage(0)
    page.mergePage(address_overlay.getPage(0))
    output_pdf.addPage(page)

    # If there are more pages, add them too
    for pageNum in range(1, original.numPages):
        output_pdf.addPage(original.getPage(pageNum))
    
    with open(output_pdf_path, 'wb') as out_file:
        output_pdf.write(out_file)

# Fields to be used from the feature class and related table
feature_fields = ["LetterRelID", "Acctnum"]
table_fields = ["LetterID", "LetterRelID", "LetterSentDate", "LetterType"]
meters_fields = ["acctnum", "owner_address1", "owner_address2", "owner_address3", "owner_address4", "owner_address5"]



# Create a dictionary to map 'acctnum' to owner_address fields from wMeters
acctnum_to_address = {}
with arcpy.da.SearchCursor(wMeters, meters_fields) as cursor:
    for row in cursor:
        # Store all owner_address fields in a list, ensuring they are added only if they are not None or empty
        address_fields = [row[i] for i in range(1, len(row)) if row[i]]
        acctnum_to_address[row[0]] = address_fields

# Editor session
edit = arcpy.da.Editor(gdb)
# Start an edit session and edit operation
edit.startEditing(False, True)
edit.startOperation()

try:
    with arcpy.da.SearchCursor(wServices, feature_fields) as cursor:
        # Read all rows into a list first
        rows = [row for row in cursor]

        # Open an InsertCursor to add records to the related table
        with arcpy.da.InsertCursor(LCRR_Letter_Tracking, table_fields) as insert_cursor:
            for row in rows:
                if row[0] is not None:  # Check if LetterRelID is not NULL
                    # Use the mapped address lines for the acctnum, if available
                    if row[1] in acctnum_to_address:
                        # Fetch the address lines from the dictionary and append the static line
                        address_lines = acctnum_to_address[row[1]] + ['cityofnewport.com/lead']
                    else:
                        # Fallback if acctnum is not found, this can be adjusted as needed
                        arcpy.AddMessage(f"Acctnum '{row[1]}' not found in wMeters. Using default address.")
                        address_lines = ["Address not found", 'cityofnewport.com/lead']
                                                          
                    # Create a new row for the related table
                    new_row = (str(uuid.uuid4()), row[0], current_date, "Postcard")  # Include a new UUID, LetterRelID, current date, and set LetterType to "Postcard"
                    # Insert the new row into the related table
                    insert_cursor.insertRow(new_row)
                    output_pdf_path = os.path.join(date_specific_folder, 'Postcard_' + row[0] + '.pdf')
                    add_multiline_address_to_pdf(template_pdf_path, output_pdf_path, address_lines)
                else:
                    arcpy.AddMessage(f"Record with Address '{row[1]}' has a NULL value in LetterRelID")
            

    # Stop the edit operation, and commit the changes
    edit.stopOperation()
    edit.stopEditing(True)
    arcpy.AddMessage("Operation completed: Records added and PDF generated.")

except Exception as e:
    # If an error occurred, abort the edit operation
    edit.abortOperation()
    arcpy.AddError(f"An error occurred: {str(e)}")



zip_file_name = datetime.datetime.now().strftime('%Y%m%d') + '_PDFs.zip'
zip_file_path = os.path.join(arcpy.env.scratchFolder, zip_file_name)

# Zip the PDFs
with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(date_specific_folder):
        for file in files:
            if file.endswith('.pdf'):
                pdf_file_path = os.path.join(root, file)
                # Here we ensure the file paths added to the zip are relative to the folder being zipped
                zipf.write(pdf_file_path, arcname=os.path.relpath(pdf_file_path, start=date_specific_folder))

# Set the zip file path as the output parameter
# Ensure the output parameter index matches your tool's configuration
arcpy.SetParameterAsText(1, zip_file_path)

# Path where you want to copy the zip file in the working_folder
destination_zip_path = os.path.join(f'{working_folder}\Zip_Folders', datetime.datetime.now().strftime('%Y%m%d%H%M') + '_PDFs.zip')

# Copy the zip file to the specified location
shutil.copy2(zip_file_path, destination_zip_path)
