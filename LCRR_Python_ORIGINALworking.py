import arcpy
import uuid
import datetime
import reportlab
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileReader, PdfFileWriter

# Set the workspace 
working_folder = r'\\MNUSLAS2NPTCX02\Data\Analysis\LCRR\Postcards'
# working_folder = r'C:\Users\JR067290\OneDrive - Jacobs\Documents\ArcGIS\Projects\Newport_LCRR'
gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NWDWaterSystem_EDIT_AGOL.sde'
# gdb = r'C:\Users\JR067290\OneDrive - Jacobs\Documents\ArcGIS\Projects\Newport_LCRR\Newport_LCRR.gdb'

arcpy.env.workspace = str(gdb)
# Feature class and related table paths
##use the fc/table in the map
# wServices = gdb + str('\DBO.wServices')
wServices = str('wServices')
# LCRR_Letter_Tracking = gdb + str('\DBO.LCRRLetterTracking')
LCRR_Letter_Tracking = str("LCRR Letter Tracking")

# Get the current date
current_date = datetime.datetime.now().strftime("%Y-%m-%d")  # Formats the date as YYYY-MM-DD


# Output PDF path
# output_pdf_path = working_folder + 'Postcards\Postcard_' + current_date + '.pdf'
template_pdf_path = f'{working_folder}\\Newport_SLM_Postcard.pdf'

def add_multiline_address_to_pdf(template_pdf_path, output_pdf_path, address_lines, x_position=288, y_position=94, line_spacing=14):
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
    address_pdf_path = 'temp_address_overlay.pdf'
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
        
           
# Determine whether to process selected features or all features
use_selected_features = False
if int(arcpy.GetCount_management(wServices)[0]) > 0:
    use_selected_features = True

# Fields to be used from the feature class and related table
feature_fields = ["LetterRelID", "PointAddress"]
table_fields = ["LetterID", "LetterRelID", "LetterSentDate", "LetterType"]

# Editor session
edit = arcpy.da.Editor(gdb)
# Start an edit session and edit operation
edit.startEditing(False, True)
edit.startOperation()

try:
    with arcpy.da.SearchCursor(wServices, feature_fields, None if use_selected_features else "LetterRelID IS NOT NULL") as cursor:
        # Read all rows into a list first
        rows = [row for row in cursor]

        # Open an InsertCursor to add records to the related table
        with arcpy.da.InsertCursor(LCRR_Letter_Tracking, table_fields) as insert_cursor:
            for row in rows:
                if row[0] is not None:  # Check if LetterRelID is not NULL
                    # Create a new row for the related table
                    new_row = (str(uuid.uuid4()), row[0], current_date, "Postcard")  # Include a new UUID, LetterRelID, current date, and set LetterType to "Postcard"
                    # Insert the new row into the related table
                    insert_cursor.insertRow(new_row)
                    # arcpy.AddMessage(f"{row[1]}")
                    address_lines = [row[1], "Newport, RI 02840", 'cityofnewport.com/lead']
                    output_pdf_path = working_folder + '\Postcard_' + row[0] + '.pdf'
                    add_multiline_address_to_pdf(template_pdf_path, output_pdf_path, address_lines)
                else:
                    arcpy.AddMessage(f"Record with Address '{row[1]}' has a NULL value in LetterRelID")
            
        # Generate the PDF with non-NULL rows
        # non_null_rows = [row for row in rows if row[0] is not None]
        # address_lines = [
        #     non_null_rows,
        #     "Newport, RI 02840",
        #     'cityofnewport.com/lead'
        #     ]
        # address_lines = [row[1], "Newport, RI 02840", 'cityofnewport.com/lead']
        # output_pdf_path = working_folder + '\Postcard_' + row[0] + '.pdf'
        # add_multiline_address_to_pdf(template_pdf_path, output_pdf_path, address_lines)

    # Stop the edit operation, and commit the changes
    edit.stopOperation()
    edit.stopEditing(True)
    arcpy.AddMessage("Operation completed: Records added and PDF generated.")

except Exception as e:
    # If an error occurred, abort the edit operation
    edit.abortOperation()
    arcpy.AddError(f"An error occurred: {str(e)}")