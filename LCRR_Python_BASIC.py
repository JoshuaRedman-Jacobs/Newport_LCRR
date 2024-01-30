import arcpy
import datetime

# Set the workspace 
working_folder = r'\\MNUSLAS2NPTCX02\Data\Analysis\LCRR\Postcards'
# gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NewportSTG.sde'
gdb = r'\\MNUSLAS2NPTCX02\Data\Connections\NWDWaterSystem_EDIT.sde'

# gdb = r'C:\Users\JR067290\OneDrive - Jacobs\Documents\ArcGIS\Projects\Newport_LCRR\Newport_LCRR.gdb'

arcpy.env.workspace = str(gdb)
# Feature class and related table paths
##use the fc/table in the map
# wServices = gdb + str('\DBO.wServices')
wServices = str('wServices')
# wServices = str('DBO.wServices')
# LCRR_Letter_Tracking = gdb + str('\DBO.LCRRLetterTracking')
LCRR_Letter_Tracking = str("LCRR Letter Tracking")

# Get the current date
current_date = datetime.datetime.now().strftime("%Y-%m-%d")  # Formats the date as YYYY-MM-DD



# Determine whether to process selected features or all features
use_selected_features = False
if int(arcpy.GetCount_management(wServices)[0]) > 0:
    use_selected_features = True

# Fields to be used from the feature class and related table
feature_fields = ["LetterRelID", "PointAddress"]
table_fields = ["LetterRelID", "LetterSentDate", "LetterType"]

# Editor session
edit = arcpy.da.Editor(gdb)
# Start an edit session and edit operation
edit.startEditing(False, True)
edit.startOperation()
try:
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


    # Stop the edit operation, and commit the changes
    edit.stopOperation()
    edit.stopEditing(True)
    print("Operation completed: Records added.")

except Exception as e:
    # If an error occurred, abort the edit operation
    edit.abortOperation()
    print("An error occurred:", str(e))