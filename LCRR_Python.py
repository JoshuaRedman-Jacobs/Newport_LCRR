import arcpy
import datetime
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Set the workspace 
working_folder = r'\\MNUSLAS2NPTCX02\Data\Analysis\LCRR\Postcards'
# gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NewportSTG.sde'
gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NWDWaterSystem_EDIT.sde'

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
table_fields = ["LetterRelID", "LetterSentDate", "LetterType"]


with arcpy.da.SearchCursor(wServices, feature_fields, None if use_selected_features else "LetterRelID IS NOT NULL") as cursor:
    # Open an InsertCursor to add records to the related table
    with arcpy.da.InsertCursor(LCRR_Letter_Tracking, table_fields) as insert_cursor:
        rows = [row for row in cursor]
        if rows:
            for row in rows:
                # Create a new row for the related table
                new_row = (row[0], current_date, "Postcard")  # Include LetterRelID, current date, and set LetterType to "Postcard"
                # Insert the new row into the related table
                insert_cursor.insertRow(new_row)
            # generate the pdf 
            generate_pdf(output_pdf, rows)



print("Operation completed: Records added and PDF generated.")
