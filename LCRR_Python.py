import arcpy
import uuid
import datetime
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Set the workspace 
# working_folder = r'\\MNUSLAS2NPTCX02\Data\Analysis\LCRR\Postcards'
working_folder = r'C:\Users\JR067290\OneDrive - Jacobs\Documents\ArcGIS\Projects\Newport_LCRR'
# gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NWDWaterSystem_EDIT_AGOL.sde'
gdb = r'C:\Users\JR067290\OneDrive - Jacobs\Documents\ArcGIS\Projects\Newport_LCRR\Newport_LCRR.gdb'

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
output_pdf = working_folder + str('\Postcard_') + current_date + str('.pdf')

####
# Avery 5160 label dimensions and layout (in points; 1 point = 1/72 inch)
label_width = 2.625 * 72  # Label width in points
label_height = 1 * 72  # Label height in points
columns = 3  # Number of columns
rows = 10  # Number of rows
top_margin = 0.5 * 72  # Top margin in points
left_margin = 0.1875 * 72  # Left margin in points
x_gap = 0.125 * 72  # Gap between columns
y_gap = 0  # Gap between rows

# Initialize PDF canvas and other related variables
def initialize_pdf(output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    x, y = left_margin, height - top_margin - label_height
    return c, width, height, x, y

# Function to draw an address label
def draw_label(c, x, y, address):
    c.drawString(x, y, address)


# Function to generate and save the PDF
def generate_pdf(output_pdf, cursor):
    c, width, height, x, y = initialize_pdf(output_pdf)

    for row in cursor:
        address = row[1] if row[1] is not None else "No Address Provided"
        draw_label(c, x, y, address)
        x += label_width + x_gap
        if x + label_width > width - left_margin:
            x = left_margin
            y -= label_height + y_gap
            if y < top_margin:
                c.showPage()
                y = height - top_margin - label_height

    c.save()
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
                else:
                    arcpy.AddMessage(f"Record with Address '{row[1]}' has a NULL value in LetterRelID")
            
        # Generate the PDF with non-NULL rows
        non_null_rows = [row for row in rows if row[0] is not None]
        generate_pdf(output_pdf, non_null_rows)

    # Stop the edit operation, and commit the changes
    edit.stopOperation()
    edit.stopEditing(True)
    arcpy.AddMessage("Operation completed: Records added and PDF generated.")

except Exception as e:
    # If an error occurred, abort the edit operation
    edit.abortOperation()
    arcpy.AddError(f"An error occurred: {str(e)}")