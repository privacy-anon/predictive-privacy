# Frequently used constants
cluster_total = 14
survey_total = 76

from google.colab import auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Authenticate and authorize using a service account
auth.authenticate_user()

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

spreadsheet_url = '' # insert sheet URL
sheet = client.open_by_url(spreadsheet_url)
worksheet = sheet.get_worksheet(0)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

df.head()

# Mute it after creating the representative data set
'''
# Select 152 profiles from each cluster evenly
import pandas as pd
import itertools
from googleapiclient.discovery import build

selected_data = []

for cluster_id in range(cluster_total):
    cluster_data = df[df['Cluster'] == cluster_id]
    selected_cluster_data = []

    if len(selected_cluster_data) < 152:
        selected_cluster_data += cluster_data.sample(n=152 - len(selected_cluster_data), random_state=42).to_dict('records')

    selected_data.extend(selected_cluster_data)

selected_df = pd.DataFrame(selected_data)
'''

for cluster_id in range(cluster_total):
    cluster_data = df[df['Cluster'] == cluster_id]

    # Separate out subsets of interest
    hiv_positive_data = cluster_data[cluster_data['HIV_STAT'] == 'positive']
    pregnant_data = cluster_data[cluster_data['PREG_STAT'] == 'Pregnant']

    # Start building our selection for this cluster in a list
    selection_list = []

    # 1) If HIV+ data exists, pick at least 1 row for sure
    hiv_count = min(4, len(hiv_positive_data))  # up to 4
    if hiv_count > 0:
        selected_hiv = hiv_positive_data.sample(n=hiv_count, random_state=42)
        selection_list.append(selected_hiv)

    # 2) If pregnant data exists, pick at least 1 row for sure
    pregnant_count = min(4, len(pregnant_data))
    if pregnant_count > 0:
        selected_pregnant = pregnant_data.sample(n=pregnant_count, random_state=43)
        # Only add if not the same row (in case one row is both HIV+ & Pregnant):
        if not selected_pregnant.index.isin(selected_hiv.index).all():
            selection_list.append(selected_pregnant)

        # Only add if it's not the exact same row as the HIV+ one selected
        # (In case the same participant is both HIV+ and Pregnant)
        if not selected_pregnant.index.isin(selected_hiv.index).all():
            selection_list.append(selected_pregnant)

    # Convert the forced picks into one DataFrame
    forced_picks = pd.concat(selection_list).drop_duplicates()

    remaining_needed = 152 - forced_picks.shape[0]
    if remaining_needed < 0:
        remaining_needed = 0

    # Exclude forced_picks from the random pool
    leftover_pool = cluster_data.drop(forced_picks.index)

    if leftover_pool.shape[0] < remaining_needed:
        print(f"Not enough rows in cluster {cluster_id} to meet the 152-row requirement.")
        selected_cluster_data = pd.concat([forced_picks, leftover_pool])
    else:
        selected_cluster_data = pd.concat([
            forced_picks,
            leftover_pool.sample(n=remaining_needed, random_state=44)
        ])

    # Finally extend your overall selection
    selected_data.extend(selected_cluster_data.to_dict('records'))

#see all HIV positive people
selected_df[selected_df['PREG_STAT'] == 'Negative']

# Mute it after creating the representative sheet
'''
new_sheet_title = 'representative_set'
new_spreadsheet = client.create(new_sheet_title)
new_worksheet = new_spreadsheet.get_worksheet(0)
new_worksheet.update_title('selected_data')
new_worksheet.update([selected_df.columns.values.tolist()] + selected_df.values.tolist())
spreadsheet_id = new_spreadsheet.id
drive_service = build('drive', 'v3', credentials=creds)

# Move the spreadsheet to the folder
try:
    drive_service.files().update(
        fileId=spreadsheet_id,
        addParents='1uJa_ZyNHqZn-YBju4kRre0HBfbcUWCSQ',
        removeParents='root',
        fields='id, parents'
    ).execute()
    print(f"New sheet '{new_sheet_title}' created and moved to the folder.")
except Exception as e:
    print(f"An error occurred while moving the file: {e}")
'''

# Added: representative sheet access
rpt_sheet_url = '' # insert sheet URL
rpt_sheet = client.open_by_url(rpt_sheet_url)

worksheet = rpt_sheet.get_worksheet(0)
data = worksheet.get_all_records()
df = pd.DataFrame(data)

df.head()

from google.colab import drive
drive.mount('/content/drive')

# Initialize a set to store unique IDs
unique_ids = set()

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random

selected_ids = []

# Mute it after creating worksheets
'''
# Added: Create 76 surveys, with each containing profiles of different clusters
import time

main_worksheet = rpt_sheet.worksheet("selected_data")
all_data = main_worksheet.get_all_records()

df = pd.DataFrame(all_data)

selected_indices = set()

for survey_num in range(survey_total):
    survey_sheet_name = f"Quiz_{survey_num + 1}"
    survey_data = []

    try:
        try:
            survey_worksheet = rpt_sheet.worksheet(survey_sheet_name)
            survey_worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            rpt_sheet.add_worksheet(title=survey_sheet_name, rows="15", cols="20")
            survey_worksheet = rpt_sheet.worksheet(survey_sheet_name)

        survey_data = []
        for cluster_id in range(cluster_total):
            cluster_data = df[df['Cluster'] == cluster_id]
            available_rows = cluster_data[~cluster_data.index.isin(selected_indices)]
            if len(available_rows) >= 2:
                selected_rows = available_rows.sample(n=2)
                survey_data.append(selected_rows)
                selected_indices.update(selected_rows.index)
            elif not available_rows.empty:
                selected_row = available_rows.sample(n=1)
                survey_data.append(selected_row)
                selected_indices.add(selected_row.index[0])

        header_row = df.columns.tolist()
        all_sheet_data = [header_row] + [list(row) for row in pd.concat(survey_data).itertuples(index=False, name=None)]

        survey_worksheet.update('A1', all_sheet_data)

    except gspread.exceptions.APIError as e:
        print(f"API Error for sheet {survey_sheet_name}: {e}")
        # Add program delay to avoid exceeding API limit
        time.sleep(5)
        continue

    except Exception as e:
        print(f"Unexpected error for sheet {survey_sheet_name}: {e}")
        break
    # Program delay
    time.sleep(2)

print("Worksheet created.")
'''

import time
import gspread
import pandas as pd

initial_information = ["NAME", "id"]
base_features = [
    "GENDER", "RACETHN", "EDUCCAT5", "DIVISION", "MARITAL_ACS",
    "CHILDRENCAT", "CITIZEN_REC", "BORN_ACS", "AGE_INT"
]
health_features = ["HIV_STAT", "PREG_STAT", "NumChronicIllness"]
finance_features = ["FAMINC5", "CC_NUM", "FDSTMP_CPS"]
sensitive_features = ["SEXUALITY", "OWNGUN_GSS", "RELIGCAT"]

def delete_unnecessary_columns(sheet_name, visible_columns, condition_label):
    worksheet = rpt_sheet.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    df['Condition'] = condition_label

    if 'Condition' not in visible_columns:
        visible_columns.append('Condition')

    columns_to_keep = [col for col in visible_columns if col in df.columns]

    if columns_to_keep:
        print(f"Sheet '{sheet_name}' - Unnecessary columns discovered and will be deleted.")
        df = df[columns_to_keep]
        worksheet.clear()
        worksheet.update('A1', [df.columns.tolist()] + df.values.tolist())
    else:
        print(f"Sheet '{sheet_name}' - Unnecessary columns may have already been deleted.")

for survey_num in range(survey_total):
    survey_sheet_name = f"Quiz_{survey_num + 1}"

    if survey_num <= 18:
        condition_label = "Control"
        visible_columns = initial_information + base_features
    elif survey_num <= 37:
        condition_label = "Health"
        visible_columns = initial_information + base_features + health_features
    elif survey_num <= 56:
        condition_label = "Finance"
        visible_columns = initial_information + base_features + finance_features
    else:
        condition_label = "Sensitive"
        visible_columns = initial_information + base_features + sensitive_features

    try:
        delete_unnecessary_columns(survey_sheet_name, visible_columns, condition_label)

        time.sleep(2)
    except gspread.exceptions.APIError as e:
        if 'RATE_LIMIT_EXCEEDED' in str(e):
            print("Rate limit exceeded. Waiting for 5 seconds before retrying...")
            time.sleep(5)
            delete_unnecessary_columns(survey_sheet_name, visible_columns, condition_label)
        else:
            print(f"Unexpected error while processing {survey_sheet_name}: {e}")
            break

print("Necessary columns have been selected.")

# Add corresponding conditions of each profile in every survey within representative data set to the last column
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time

scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

rpt_sheet_url = '' # insert sheet URL
sheet = client.open_by_url(rpt_sheet_url)

sheet_names = [f"Quiz_{i}" for i in range(1, 41)]

for sheet_name in sheet_names:
    worksheet = sheet.worksheet(sheet_name)

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    if 'Condition' not in df.columns:
        if 1 <= int(sheet_name.split('_')[1]) <= 10:
            df['Condition'] = 'Base'
        elif 11 <= int(sheet_name.split('_')[1]) <= 20:
            df['Condition'] = 'Base + Health'
        elif 21 <= int(sheet_name.split('_')[1]) <= 30:
            df['Condition'] = 'Base + Finance'
        elif 31 <= int(sheet_name.split('_')[1]) <= 40:
            df['Condition'] = 'Base + Sensitive'

        header = df.columns.tolist()
        worksheet.update([header] + df.values.tolist())
        print(f"Updated {sheet_name} with 'Condition' column.")

    time.sleep(2)

print("Conditions have been added to each profile in every survey.")

# Integrating each profile and condition to another sheet called integration.
# It moves values intermittently to minimize the probability of API runtime error occurrence.
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

rpt_sheet_url = '' # insert sheet URL
spreadsheet = client.open_by_url(rpt_sheet_url)

try:
    integration_sheet = spreadsheet.add_worksheet(title="integration", rows="1000", cols="26")  # Default 26 columns for flexibility
except Exception as e:
    integration_sheet = spreadsheet.worksheet("integration")

integration_sheet.update("A1:B1000", [[""]] * 1000)
integration_sheet.update('A1', [["id", "Condition"]])

row_index = 2

for i in range(66, 77): # If API runtime error occurs, delete the incomplete area and adjust the range
    sheet_name = f"Quiz_{i}"
    quiz_sheet = spreadsheet.worksheet(sheet_name)
    data = quiz_sheet.get_all_values()[1:]
    rows_to_add = []
    for row in data:
        rows_to_add.append([row[1], row[-1]])
    cell_range = f"A{row_index}:B{row_index + len(rows_to_add) - 1}"
    try:
        integration_sheet.update(cell_range, rows_to_add)
    except Exception as e:
        time.sleep(5)
        integration_sheet.update(cell_range, rows_to_add)
    row_index += len(rows_to_add)
    time.sleep(1)

# Add corresponding conditions of each profile in Sheet 3 of update counter file to the last column
# Changing less than 5 surveys each time running can minimize API error probability
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

rpt_sheet_url = '' # insert sheet URL
update_sheet_url = '' # insert sheet URL

rpt_sheet = client.open_by_url(rpt_sheet_url)
update_sheet = client.open_by_url(update_sheet_url).worksheet("Sheet4")

integration_sheet = rpt_sheet.worksheet("integration")

integration_data = integration_sheet.get_all_values()[1:]
integration_dict = {str(row[0]): row[1] for row in integration_data}

sheet3_data = update_sheet.get_all_values()
header = sheet3_data[0]
rows = sheet3_data[1:]

if 'Condition' not in header:
    header.append('Condition')
    update_sheet.update('A1', [header])

updated_rows = []
for row in rows:
    person_id = str(row[0])
    condition = integration_dict.get(person_id, 'Unknown')
    if len(row) < len(header):
        row.append(condition)
    else:
        row[-1] = condition
    updated_rows.append(row)

update_sheet.update(f"A2:{chr(64 + len(header))}{len(rows) + 1}", updated_rows)

print("Conditions have been added to the Sheet4 of update counter table.")

def create_description(data_row):
    # Basic features
    name = data_row['NAME']
    id = data_row['id']

    gender = data_row['GENDER'].lower()
    if gender == 'male':
        pronoun = 'He'
        pronoun2 = 'His'
    else:
        pronoun = 'She'
        pronoun2 = 'Her'

    racethn = data_row['RACETHN']
    if racethn == "Other race":
        racethn = "unidentified"

    educcat5 = data_row['EDUCCAT5'].lower()
    if educcat5 == 'less than hs':
        educcat5 = 'a less than high school'
    elif educcat5 == 'hs grad':
        educcat5 = 'a high school graduate'
    elif educcat5 == 'some college':
        educcat5 = 'some college'
    elif educcat5 == 'College grad':
        educcat5 = 'a college graduate'
    else:
        educcat5 = 'a postgraduate'

    marital_acs = data_row['MARITAL_ACS'].lower()
    if marital_acs == 'never married':
        marital_acs = 'has never married'
    elif marital_acs == 'now married':
        marital_acs = 'is now married'
    else:
        marital_acs = 'is divorced'

    childrencat = data_row['CHILDRENCAT'].lower()
    if childrencat == "no children":
        childrencat = "doesn't have"
    else:
        childrencat = "has"

    born_acs = data_row['BORN_ACS']
    if born_acs == 'Inside the United States':
      born_acs = 'inside the U.S.'
    else:
      born_acs = 'outside the U.S.'

    age_int = data_row['AGE_INT']

    citizen_rec = data_row['CITIZEN_REC'].lower()
    if citizen_rec == 'Yes, a U.S. citizen':
        citizen_rec = "US citizen"
    else:
        citizen_rec = "non-US citizen"

    division = data_row['DIVISION']

    division_to_common_name = {
    'Pacific': 'the West Coast',
    'Mountain': 'the Mountain States',
    'West North Central': 'the Upper Midwest',
    'West South Central': 'the South Central',
    'East North Central': 'the Great Lakes region',
    'East South Central': 'the Deep South',
    'South Atlantic': 'the South',
    'Middle Atlantic': 'the Northeast',
    'New England': 'New England'
}

    if division in division_to_common_name:
        division = division_to_common_name[division]
    else:
        division = ""

    base_description = (
        f"{name} has the following attributes:\r"
        f"• {pronoun2} age is between {age_int} years.\r"
        f"• {pronoun} is of {racethn} descent.\r"
        f"• {pronoun2} gender is {gender}.\r"
        f"• {pronoun} has {educcat5} level education.\r"
        f"• {pronoun} {marital_acs}.\r"
        f"• {pronoun} {childrencat} children.\r"
        f"• {pronoun} is a {citizen_rec}.\r"
        f"• {pronoun} was born {born_acs}\r"
        f"• {pronoun} resides in {division} region of the U.S.\r"
    )

    # Health features
    hiv = data_row.get('HIV_STAT', None)
    if hiv:
        hiv = hiv.lower()

    pregnancy = data_row.get('PREG_STAT', None)
    if pregnancy:
        if gender == 'male':
          pregnancy = ""
        else:
            pregnancy = data_row.get('PREG_STAT', None)
            if pregnancy == 'Positive':
                pregnancy = "• She is pregnant.\r"
            else:
                pregnancy = "• She is not pregnant.\r"

    num_chronic_illness = data_row.get('NumChronicIllness', None)
    if isinstance(num_chronic_illness, (int, float)):
        num_chronic_illness = str(num_chronic_illness)
        num_chronic_illness = num_chronic_illness.lower()
        if num_chronic_illness == '0':
            chronill = 'not chronically ill'
        else:
            chronill = 'chronically ill'

    if hiv and num_chronic_illness:
        health_description = (
            f"• {pronoun2} HIV status is {hiv}.\r"
            f"{pregnancy}"
            f"• {pronoun} is {chronill}.\r"
        )
    else:
        health_description = ""

    # finance features
    faminc5 = data_row.get('FAMINC5', None)
    if faminc5:
        faminc5.lower()
        if faminc5 == '$20K to less than $40K':
            faminc5 = 'between $20K to less than $40K'
        elif faminc5 == '$40K to less than $75K':
            faminc5 = 'between $40K to less than $75K'
        elif faminc5 == '$75K to less than $150K':
            faminc5 = 'between $75K to less than $150K'
        else:
            None

    cred = data_row.get('CC_NUM', None)
    if cred:
        if isinstance(cred, (int, float)):
            cred = str(cred)
        cred = cred.lower()
        if cred != 0:
            cred = "has"
        else:
            cred = "does not have"

    fdstmp_cps =  data_row.get('FDSTMP_CPS', None)
    if fdstmp_cps == 'yes':
        fdstmp_cps = "currently receives foodstamps"
    else:
        fdstmp_cps = "does not currently receive foodstamps"

    if faminc5 and cred and fdstmp_cps:
        finance_description = (
            f"• {pronoun2} family's annual income is {faminc5}.\r"
            f"• {pronoun} {cred} a credit card.\r"
            f"• {pronoun} {fdstmp_cps}.\r"
        )
    else:
        finance_description = ""

    # sensitive features
    sexuality = data_row.get('SEXUALITY', None)
    if sexuality:
        sexuality = sexuality.lower()

    owngun_gss = data_row.get('OWNGUN_GSS', None)
    if owngun_gss == 'Yes':
        owngun_gss = "owns a gun"
    else:
        owngun_gss = "doesn't own a gun"

    religcat = data_row.get('RELIGCAT', None)

    if sexuality and religcat and owngun_gss:
        sensitive_description = (
            f"• {pronoun} is {sexuality}.\r"
            f"• {pronoun} {owngun_gss}.\r"
            f"• {pronoun} is {religcat}.\r"
        )
    else:
      sensitive_description = ""

    description = base_description + health_description + finance_description + sensitive_description

    return description

# Mute it after creating forms and URLs
'''
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread

# Authentication and service setup
service_account_key_path = 'credentials.json'
credentials = service_account.Credentials.from_service_account_file(
    service_account_key_path,
    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
)
client = gspread.authorize(credentials)
forms_service = build("forms", "v1", credentials=credentials)

# Open the source and destination spreadsheets
source_spreadsheet = client.open_by_url('')  # insert sheet URL
destination_spreadsheet = client.open_by_url('')  # insert sheet URL
summary_worksheet = destination_spreadsheet.sheet1

# Prepare the destination worksheet
summary_worksheet.update('A1:B1', [["Quiz Name", "Form URL"]])

# Iterate through each survey, create forms, and log URLs
for i, worksheet in enumerate(source_spreadsheet.worksheets()[1:]):
    survey_name = worksheet.title
    form_body = {"info": {"title": f"Harm Scores Survey: {survey_name}"}}
    result = forms_service.forms().create(body=form_body).execute()
    form_id = result["formId"]
    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    summary_worksheet.append_row([survey_name, form_url])

print("All surveys and form URLs have been logged.")
'''

import re
import pandas as pd
import time

summary_worksheet = destination_spreadsheet.worksheet('Sheet1')
form_urls_records = summary_worksheet.get_all_records()

for record in form_urls_records:
    quiz_name = record['Quiz Name']
    form_url = record['Form URL']

    form_id_match = re.search(r'/d/(.*?)/edit', form_url)
    if form_id_match:
        form_id = form_id_match.group(1)
        matching_worksheet = source_spreadsheet.worksheet(quiz_name)
        # Assuming each row in the worksheet is a person's information
        person_records = matching_worksheet.get_all_records()
        if not person_records:
            print(f"No data found in the worksheet for quiz: {quiz_name}")
            continue

        df_worksheet = pd.DataFrame(person_records)

        df_worksheet['Description'] = ''

        for index, row in df_worksheet.iterrows():
            full_description = create_description(row)
            df_worksheet.at[index, 'Description'] = full_description

        update_requests = []

        first_request = {
            "createItem": {
                "item": {
                    "textItem": {},
                    "title": f"We are trying to quantify harm from the release of personal information. Please answer each question to the best of your abilities. For each subject, read the entire profile—sometimes, the harm might (or might not) be context-dependent.\
                              \r\rAll of the people included in this survey are fake (synthetic)—we are not showing you real data about real people. This study is IRB approved."
                },
                "location": {"index": 0},
            },
        }
        update_requests.append(first_request)

        break_request = {
            "createItem": {
                "item": {
                    "pageBreakItem": {},
                  },
                  "location": {"index": 1},
            },
        }

        update_requests.append(break_request)

        prolific_id =  {
             "createItem": {
                 "item": {
                    "title": "What is your Prolific ID?",
                       "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                },

                            },
                        },
                    },
                    "location": {"index": 2},
                },
            }

        update_requests.append(prolific_id)

        break_request = {
            "createItem": {
                "item": {
                    "pageBreakItem": {},
                  },
                  "location": {"index": 3},
            },
        }

        update_requests.append(break_request)

        question_number = 1
        location_index = 4
        row_count = 0

        for index, row in df_worksheet.iterrows():
            row_count += 1
            description_value = row['Description']
            id = row['id']
            description_request = {
                "createItem": {
                    "item": {
                        "textItem": {},
                        "title": f"Sample person {question_number}\r\r{description_value}"
                    },
                    "location": {"index": location_index},
                },
            }

            update_requests.append(description_request)
            question_number += 1
            location_index += 1

            attention_check =  {
                "createItem": {
                    "item": {
                        "title": "What is this person's ID number? (Please select the given answer; this question is purely for data processing purposes.)",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": f"{id}"},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }

            update_requests.append(attention_check)
            location_index += 1

            if row_count == 10:
                attention_check2 = {
                "createItem": {
                    "item": {
                        "title": "What do you hope elected leaders in Washington do in the next year? This is an attention check question.",
                          "questionItem": {
                                "question": {
                                    "required": True,
                                    "textQuestion": {
                                    },

                                },
                            },
                        },
                        "location": {"index": location_index},
                    },
                }
                update_requests.append(attention_check2)
                location_index += 1

            else:
                attention_check2 = {}

            if row_count == 20:
                attention_check3 =  {
                "createItem": {
                    "item": {
                        "title": "To ensure that you have read this question carefully, please type “Green” as your answer. This is an attention check question.",
                          "questionItem": {
                                "question": {
                                    "required": True,
                                    "textQuestion": {
                                    },

                                },
                            },
                        },
                        "location": {"index": location_index},
                    },
                }
                update_requests.append(attention_check3)
                location_index += 1

            else:
                attention_check3 = {}

            name = row['NAME']
            gender = row['GENDER'].lower()
            if gender == 'male':
                pronoun2 = 'his'
            else:
                pronoun2 = 'her'

            q1_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if hackers or cybercriminals stole {name}'s personal data in a data breach?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q1_request)
            location_index += 1

            q2_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if government agencies accessed {name}'s personal information without {pronoun2} knowledge or consent?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q2_request)
            location_index += 1

            q3_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if a corporation collected and used {name}'s personal data for {pronoun2} own purposes without {pronoun2} consent?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q3_request)
            location_index += 1

            q4_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if {name}'s employer or colleagues viewed {pronoun2} personal data without {pronoun2} permission?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q4_request)
            location_index += 1

            q5_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if {name}'s personal information was inadvertently shared with {pronoun2} family members without {pronoun2} consent?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q5_request)
            location_index += 1

            q6_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if personal details about {name} were disclosed to {pronoun2} close friends without {pronoun2} knowledge?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q6_request)
            location_index += 1

            q7_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if {name}'s personal data was accessed by acquaintances who know {name} by face and name but don't interact with {name} regularly?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q7_request)
            location_index += 1

            q8_request = {
                "createItem": {
                    "item": {
                        "title": f"How harmful do you think most people in the U.S. would consider it if {name}'s personal information was made publicly available on the internet for anyone to access without {pronoun2} consent?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": 'Not at all harmful'},
                                        {"value": 'Slightly harmful'},
                                        {"value": 'Moderately harmful'},
                                        {"value": 'Very harmful'},
                                        {"value": 'Extremely harmful'},
                                    ],
                                },
                            },
                        },
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(q8_request)
            location_index += 1

            break_request = {
                "createItem": {
                    "item": {
                        "pageBreakItem": {},
                    },
                    "location": {"index": location_index},
                },
            }
            update_requests.append(break_request)
            location_index += 1

            update = {"requests": update_requests}

        last_request = {
            "createItem": {
                "item": {
                    "textItem": {},
                    "title": f"Prolific code: COLYGFMB"
                },
                "location": {"index": location_index},
            },
        }
        update_requests.append(last_request)
        location_index += 1

        try:
          t = "Harm Scores Survey"
          forms_service.forms().batchUpdate(formId=form_id, body={"requests": update_requests}).execute()

          drive_service = build('drive', 'v3', credentials=credentials)
          # Temporarily muted

          drive_service.permissions().create(
              fileId=form_id,
              body={
                  'role': 'writer',
                  'type': 'user',
                  'emailAddress': '' #insert your email here
              }
          ).execute()

          print(f"Form updated successfully: {form_id}")
        except Exception as e:
          print(f"Unable to update form {form_id}: {e}")
    else:
        print(f"Unable to extract form ID from URL: {form_url}")
    # Program delay
    time.sleep(2)

# Muted after creating a sheet with certainty
'''
from google.colab import auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from gspread_dataframe import set_with_dataframe

# Added: representative sheet with certainty access
auth.authenticate_user()
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
rpt_sheet_cty_url = '' # insert sheet URL
rpt_sheet_cty = client.open_by_url(rpt_sheet_cty_url)
worksheet = rpt_sheet_cty.worksheet("selected_data")
data = worksheet.get_all_records()
df = pd.DataFrame(data)

def replicate_rows_with_certainty(row):
    replicated_rows = []
    for certainty in [50, 75, 100]:
        new_row = row.copy()
        new_row['certainty'] = certainty
        replicated_rows.append(new_row)
    return replicated_rows

transformed_rows = []
for _, row in df.iterrows():
    transformed_rows.extend(replicate_rows_with_certainty(row))

transformed_df = pd.DataFrame(transformed_rows)

worksheet.clear()
columns = transformed_df.columns.values.tolist()
worksheet.update([columns] + transformed_df.values.tolist())

transformed_df.head()
'''

"""After experiment"""

# Temporarily muted
'''
import scipy.stats as stats

anova_df = df_updated[['RACETHN', 'AGE_INT', 'SEXUALITY', 'EDUCCAT5', 'scores']].dropna()
groups = [group['scores'].values for name, group in anova_df.groupby(['EDUCCAT5'])]

# Perform ANOVA
f_stat, p_value = stats.f_oneway(*groups)
print('ANOVA result: F-statistic = {:.2f}, p-value = {:.3f}'.format(f_stat, p_value))
'''

# df_updated.to_csv('harm3.csv', index=False)
