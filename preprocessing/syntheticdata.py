"""SyntheticData.ipynb
# Import Pew Research Center Dataset
Synthetic dataset found [here](https://www.pewresearch.org/methods/2018/01/26/appendix-b-synthetic-population-dataset/). This dataset is representative of the USA population. We will first examine the existing dataset and then modify it to include more columns of data that are also statistically representative of the USA population.
"""

pip install pyreadstat

"""Load synthetic data."""

import pandas as pd
import pyreadstat

pop_df = pd.read_spss('synthetic_population_dataset.sav')
pop_df.head()

pop_df.tail()

"""# Appending new columns of data

#LGBTQ+

## LGBTQ+
Pew Research says 7% of Americans are LGBTQ+, [link](https://www.pewresearch.org/short-reads/2023/06/23/5-key-findings-about-lgbtq-americans/#:~:text=Some%207%25%20of%20Americans%20are,across%20racial%20and%20ethnic%20groups.), so 23.33 mil.
"""

import pandas as pd
import numpy as np

# Assuming 'pop_df' is your DataFrame
# Initialize 'SEXUALITY' column with default value
pop_df['SEXUALITY'] = 'Heterosexual'

# Generate random probabilities
prob_lgb = np.random.uniform(0, 1, len(pop_df)) <= 0.07

# Assign 'Lesbian, Gay, or Bisexual' based on probabilities
pop_df.loc[prob_lgb, 'SEXUALITY'] = 'Lesbian, Gay, or Bisexual'

# "Among Americans who are lesbian, gay or bisexual, the vast majority of women say they are bisexual (79%) while the majority of men say they are gay (57%)." (Pew Research Center)
female_lgb = pop_df[prob_lgb & (pop_df['GENDER'] == 'Female')]
prob_bisexual_female = np.random.uniform(0, 1, len(female_lgb)) <= 0.79
pop_df.loc[female_lgb.index, 'SEXUALITY'] = np.where(prob_bisexual_female, 'Bisexual', 'Lesbian')
male_lgb = pop_df[prob_lgb & (pop_df['GENDER'] == 'Male')]
prob_gay_male = np.random.uniform(0, 1, len(male_lgb)) <= 0.57
pop_df.loc[male_lgb.index, 'SEXUALITY'] = np.where(prob_gay_male, 'Gay', 'Bisexual')

# Ensure at least one gay and one lesbian person in each racial group and religious group
racial_groups = pop_df['RACETHN'].unique()
religious_groups = pop_df['RELIGCAT'].unique()

for race in racial_groups:
    for religion in religious_groups:
        subset = pop_df[(pop_df['RACETHN'] == race) & (pop_df['RELIGCAT'] == religion)]

        if 'Gay' not in subset['SEXUALITY'].values:
            males = subset[subset['GENDER'] == 'Male']
            if not males.empty:
                index = males.sample(1).index
                pop_df.loc[index, 'SEXUALITY'] = 'Gay'
            else:
                females = subset[subset['GENDER'] == 'Female']
                if not females.empty:
                    index = females.sample(1).index
                    pop_df.loc[index, 'SEXUALITY'] = 'Gay'

        if 'Lesbian' not in subset['SEXUALITY'].values:
            females = subset[subset['GENDER'] == 'Female']
            if not females.empty:
                index = females.sample(1).index
                pop_df.loc[index, 'SEXUALITY'] = 'Lesbian'
            else:
                males = subset[subset['GENDER'] == 'Male']
                if not males.empty:
                    index = males.sample(1).index
                    pop_df.loc[index, 'SEXUALITY'] = 'Lesbian'

# Verify the adjustments
for race in racial_groups:
    for religion in religious_groups:
        subset = pop_df[(pop_df['RACETHN'] == race) & (pop_df['RELIGCAT'] == religion)]
        assert 'Gay' in subset['SEXUALITY'].values, f"Missing 'Gay' person in {race} and {religion}"
        assert 'Lesbian' in subset['SEXUALITY'].values, f"Missing 'Lesbian' person in {race} and {religion}"

# Group by 'GENDER' and 'SEXUALITY' and calculate the size (counts) of each group
distribution_gender_sxly = pop_df.groupby(['GENDER', 'SEXUALITY'], observed=True).size()

# Calculate the percentage distribution within each gender
distribution_gender_sxly = distribution_gender_sxly.groupby(level=0, observed=True).apply(lambda x: 100 * x / x.sum())

# Print the result
print(distribution_gender_sxly)

"""## HIV Status
Approximately 0.03% - 0.07% of the country is infected with HIV, which
 we will call the real USA range. So, we mimic this distribution based on age, region, and race.  The final distribution of the sample (ratio of people that have HIV to people that do not) should be close to or in the real USA range.

Generate synthetic data for HIV status based on 2021 data from [healthequitytracker.org](https://healthequitytracker.org/exploredata?mls=1.hiv-3.00&mlp=disparity&dt1=hiv_prevalence&demo=race_and_ethnicity). Regional information [here](https://www2.census.gov/geo/pdfs/maps-data/maps/reference/us_regdiv.pdf). Metric: HIV prevalance.

Pew Research says 7% of Americans are LGBTQ+, [link](https://www.pewresearch.org/short-reads/2023/06/23/5-key-findings-about-lgbtq-americans/#:~:text=Some%207%25%20of%20Americans%20are,across%20racial%20and%20ethnic%20groups.), so 23.33 mil.

Note: Percents add up to 99% because 1% of HIV cases come from US dependent regions not used in this dataset.

Region data [here](https://www.ruralhealthresearch.org/publications/1414#:~:text=The%20Northeast%20has%20the%20highest,Midwest%20(205%20per%20100%2C000).)

Here, we acquire the data from the Atlas db for the prevalance rates per state and then crunch them into the regional divisions.
"""

file_path = 'GeographyChartData.csv'
df = pd.read_csv(file_path)

# Correcting the column name to match the DataFrame
df = df[['Geography', 'Rate per 100000']]

# Defining the divisions
divisions = {
    'New England': ['Connecticut', 'Maine', 'Massachusetts', 'New Hampshire', 'Rhode Island', 'Vermont'],
    'Middle Atlantic': ['New Jersey', 'New York', 'Pennsylvania'],
    'East North Central': ['Illinois', 'Indiana', 'Michigan', 'Ohio', 'Wisconsin'],
    'West North Central': ['Iowa', 'Kansas', 'Minnesota', 'Missouri', 'Nebraska', 'North Dakota', 'South Dakota'],
    'South Atlantic': ['Delaware', 'Florida', 'Georgia', 'Maryland', 'North Carolina', 'South Carolina', 'Virginia', 'Washington, D.C.', 'West Virginia'],
    'East South Central': ['Alabama', 'Kentucky', 'Mississippi', 'Tennessee'],
    'West South Central': ['Arkansas', 'Louisiana', 'Oklahoma', 'Texas'],
    'Mountain': ['Arizona', 'Colorado', 'Idaho', 'Montana', 'Nevada', 'New Mexico', 'Utah', 'Wyoming'],
    'Pacific': ['Alaska', 'California', 'Hawaii', 'Oregon', 'Washington']
}

# Calculate the average rate per division
division_rates = {}
for division, states in divisions.items():
    division_df = df[df['Geography'].isin(states)]
    avg_rate = division_df['Rate per 100000'].mean()
    division_rates[division] = avg_rate

division_rates

import pandas as pd
import numpy as np

# Assuming you have a DataFrame named pop_df with columns ['DIVISION', 'RACETHN', 'AGE']

def generate_HIV_status(row):
    # Define the probabilities based on conditions
    division_probabilities = {
        'New England': 0.2256,
        'Middle Atlantic': 0.5015,
        'East North Central': 0.2251,
        'West North Central': 0.1462,
        'South Atlantic': 0.4917,
        'East South Central': 0.2886,
        'West South Central': 0.3554,
        'Mountain': 0.1974,
        'Pacific': 0.2311
    }

    racethn_probabilities = { # from Atlas db
        'Black non-Hispanic': 1.23,  # Rate for African Americans
        'White non-Hispanic': 0.176,
        'Asian': 0.097,
        'Hispanic': 0.520,           # Rate for Hispanic/Latino persons
        'Other race': 0.482  # avg between indig, native american, multi race
    }

    age_probabilities = {
        (13, 24): 0.053, # ages are from Atlas db
        (25, 34): 0.340,  # Rate for persons aged 25-34
        (35, 44): 0.470,   # Rate for persons aged 35-44
        (45, 54): 0.597,
        (55, 64): 0.677,
        (65, 100): 0.255

    }

    sexuality_probabilities = {
        'Heterosexual': 0.2, # 333.3 mil * 85.6% of the pop is het = 285.3 tot het people; tweeked within range of error for some more samples
        'Lesbian': 0.067,
        'Bisexual': 1.28, # MSM + HET + Other / 3 / tot LGBTQ pop
        'Gay': 2.63 # MSM num from Atlas db / half of LGBTQ pop (since only men)
    }

    gender_probabilities = {
        'Female': 0.172, # 173 per 100000 * 100
        'Male': 0.594 # 598 per 100000 * 100
    }

      # Apply division probabilities
    division_prob = division_probabilities.get(row['DIVISION'], 0)

    # Apply race/ethnicity adjustments
    racethn_adjustment = racethn_probabilities.get(row['RACETHN'], 1)

    # Apply age adjustments
    age_adjustment = next((adjust for (age_min, age_max), adjust in age_probabilities.items() if age_min <= row['AGE'] <= age_max), 1)

    # Apply sexuality adjustments
    sexuality_adjustment = sexuality_probabilities.get(row['SEXUALITY'], 1)

    # Apply gender adjustments
    gender_adjustment = gender_probabilities.get(row['GENDER'], 1)

    # Calculate the combined probability
    combined_prob = division_prob * racethn_adjustment * age_adjustment * sexuality_adjustment * gender_adjustment

    # Generate HIV status based on combined probability
    if np.random.rand() <= combined_prob:
        return 'positive'
    else:
        return 'negative'

# Apply the function to create the new column 'HIV_STAT'
pop_df['HIV_STAT'] = pop_df.apply(generate_HIV_status, axis=1)

pop_df.head()

pop_df.tail()

"""Check synthetic data distribution."""

distribution = pop_df.groupby(['DIVISION', 'HIV_STAT']).size().groupby(level=0).apply(lambda x: 100 * x / x.sum())

# Print the distribution
print(distribution)

distribution = pop_df.groupby(['RACETHN', 'HIV_STAT']).size().groupby(level=0).apply(lambda x: 100 * x / x.sum())
print(distribution)

distribution = pop_df.groupby(['AGE', 'HIV_STAT']).size().groupby(level=0).apply(lambda x: 100 * x / x.sum())
print(distribution)

distribution = pop_df.groupby(['SEXUALITY', 'HIV_STAT']).size().groupby(level=0).apply(lambda x: 100 * x / x.sum())
print(distribution)

"""Check HIV prevelance in sample to confirm. USA population is currently at 0.3% people."""

pop_df['HIV_STAT'].value_counts()

"""## Pregnancy Status

Best source for pregnancy status: [here](https://www.cdc.gov/nchs/data/series/sr_02/sr02-201.pdf)

Check the unique values in the gender column.
"""

# Get unique values in 'Column_Name'
gender = pop_df['MARITAL_ACS'].unique()

# Convert to a set
gender_set = set(gender)

print(gender_set)

import pandas as pd
import numpy as np

# Data provided in the problem
total_female_population = 166.58 * 10**6  # in millions
total_pregnancies_2019 = 5.507 * 10**6  # in millions

# Pregnancy rates per 1,000 females for different groups in 2019
pregnancy_rates_2019 = {
    'total': 85.6,
    'age_15_19': 29.4,
    'age_20_24': 98.8,
    'age_25_29': 132.6,
    'age_30_34': 139.7,
    'age_35_39': 77.0,
    'age_40_plus': 24.7,
    'hispanic': 85.5,
    'non_hispanic_black': 109.8,
    'non_hispanic_white': 82.6,
    'non_hispanic_other': 68.7,
    'unmarried': 66.4,
    'married': 115.7
}

# Assuming pop_df exists, categorize the age and calculate weighted pregnancy probabilities
def calculate_age_group(age):
    if 15 <= age <= 19:
        return 'age_15_19'
    elif 20 <= age <= 24:
        return 'age_20_24'
    elif 25 <= age <= 29:
        return 'age_25_29'
    elif 30 <= age <= 34:
        return 'age_30_34'
    elif 35 <= age <= 39:
        return 'age_35_39'
    else:
        return 'age_40_plus'

def calculate_pregnancy_probability(row):
    # Automatically assign 'Not Applicable' for males
    if row['GENDER'] == 'Male':
        return 'Not Applicable'

    # Age-based probability
    age_group = calculate_age_group(row['AGE'])
    age_based_prob = pregnancy_rates_2019[age_group] / 1000

    # Race-based adjustment
    if row['RACETHN'] == 'Hispanic':
        race_based_prob = pregnancy_rates_2019['hispanic'] / 1000
    elif row['RACETHN'] == 'Black non-Hispanic':
        race_based_prob = pregnancy_rates_2019['non_hispanic_black'] / 1000
    elif row['RACETHN'] == 'White non-Hispanic':
        race_based_prob = pregnancy_rates_2019['non_hispanic_white'] / 1000
    else:  # Other non-Hispanic races
        race_based_prob = pregnancy_rates_2019['non_hispanic_other'] / 1000

    # Marital status adjustment
    if row['MARITAL_ACS'] == 'Now married':
        marital_based_prob = pregnancy_rates_2019['married'] / 1000
    else:
        marital_based_prob = pregnancy_rates_2019['unmarried'] / 1000

    # Combine probabilities (taking an average for simplicity)
    combined_prob = (age_based_prob + race_based_prob + marital_based_prob) / 3

    # Return 'Positive' or 'Negative' based on combined probability
    return np.random.choice(['Positive', 'Negative'], p=[combined_prob, 1 - combined_prob])

# Assuming pop_df exists and has the columns AGE, RACETHN, and MARITAL_ACS
# Here we create a mock pop_df for demonstration
np.random.seed(0)  # For reproducibility

# Apply the function to calculate pregnancy status
pop_df['PREG_STAT'] = pop_df.apply(calculate_pregnancy_probability, axis=1)

"""Source: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6501574/"""

pop_df.head()

pop_df.tail()

preg_stat_by_ethnicity = pop_df.groupby(['RACETHN', 'PREG_STAT']).size().unstack(fill_value=0)
print(preg_stat_by_ethnicity)

#pop_df.to_csv('synthetic_population_dataset.csv')

"""#Religion: Include Non-Christian Distribution

Source: [Pew Research](https://www.pewresearch.org/religion/religious-landscape-study/)

Specific stats:


*   [Hinduism](https://www.pewresearch.org/religion/2023/10/11/hinduism-among-asian-americans/)
"""

# Get unique values in 'Column_Name'
religion = pop_df['RELIGCAT'].unique()

# Convert to a set
religion_set = set(religion)

print(religion_set)

"""Example

If an individual is 40 years old, the function will:

* Identify the age interval as 30-49.
* Retrieve the probability associated with the 30-49 age group for each religion.
* Combine this probability with the probabilities based on race and gender to get an overall probability for each religion.
* Use these probabilities to randomly select a religion.
"""

# Define distributions by demographic groups
religion_race_stats = {
    'Buddhist': {'White non-Hispanic': 44, 'Black non-Hispanic': 3, 'Asian': 33, 'Hispanic': 12, 'Other race': 8},
    'Jehovah\'s Witness': {'White non-Hispanic': 36, 'Black non-Hispanic': 27, 'Asian': 0, 'Hispanic': 32, 'Other race': 6},
    'Jewish': {'White non-Hispanic': 90, 'Black non-Hispanic': 2, 'Asian': 2, 'Hispanic': 4, 'Other race': 2},
    'Mormon': {'White non-Hispanic': 85, 'Black non-Hispanic': 1, 'Asian': 1, 'Hispanic': 8, 'Other race': 5},
    'Muslim': {'White non-Hispanic': 38, 'Black non-Hispanic': 28, 'Asian': 28, 'Hispanic': 4, 'Other race': 3},
    'Evangelical Protestant': {'White non-Hispanic': 76, 'Black non-Hispanic': 6, 'Asian': 2, 'Hispanic': 11, 'Other race': 5},
    'Mainline Protestant': {'White non-Hispanic': 86, 'Black non-Hispanic': 3, 'Asian': 1, 'Hispanic': 6, 'Other race': 3},
    'Unaffiliated': {'White non-Hispanic': 68, 'Black non-Hispanic': 9, 'Asian': 5, 'Hispanic': 13, 'Other race': 4},
    'Hindu': {'White non-Hispanic': 4, 'Black non-Hispanic': 2, 'Asian': 91, 'Hispanic': 1, 'Other race': 2}, # modified since most hindus are asian, but most asians aren't necessarily hindu
    'Orthodox Christian': {'White non-Hispanic': 81, 'Black non-Hispanic': 8, 'Asian': 3, 'Hispanic': 6, 'Other race': 2}
}

religion_age_stats = {
    'Buddhist': {'18-29': 34, '30-49': 30, '50-64': 23, '65-100': 14},
    'Jehovah\'s Witness': {'18-29': 15, '30-49': 34, '50-64': 29, '65-100': 23},
    'Jewish': {'18-29': 22, '30-49': 27, '50-64': 26, '65-100': 26},
    'Mormon': {'18-29': 22, '30-49': 40, '50-64': 22, '65-100': 16},
    'Muslim': {'18-29': 44, '30-49': 37, '50-64': 13, '65-100': 5},
    'Evangelical Protestant': {'18-29': 17, '30-49': 33, '50-64': 29, '65-100': 20},
    'Mainline Protestant': {'18-29': 16, '30-49': 29, '50-64': 29, '65-100': 26},
    'Unaffiliated': {'18-29': 35, '30-49': 37, '50-64': 19, '65-100': 9},
    'Hindu': {'18-29': 34, '30-49': 56, '50-64': 6, '65-100': 4},
    'Orthodox Christian': {'18-29': 26, '30-49': 40, '50-64': 21, '65-100': 13}
}

religion_gender_stats = {
    'Buddhist': {'Female': 49, 'Male': 51},
    'Jehovah\'s Witness': {'Female': 65, 'Male': 35},
    'Jewish': {'Female': 48, 'Male': 52},
    'Mormon': {'Female': 54, 'Male': 46},
    'Muslim': {'Female': 35, 'Male': 65},
    'Evangelical Protestant': {'Female': 55, 'Male': 45},
    'Mainline Protestant': {'Female': 55, 'Male': 45},
    'Unaffiliated': {'Female': 43, 'Male': 57},
    'Hindu': {'Female': 38, 'Male': 62},
    'Orthodox Christian': {'Female': 44, 'Male': 56}
}

religion_marital_stats = {
    'Buddhist': {'Now married': 39, 'Living with a partner': 11, 'Divorced': 10, 'Widowed': 3, 'Never married': 37},
    'Jehovah\'s Witness': {'Now married': 53, 'Living with a partner': 5, 'Divorced': 12, 'Widowed': 8, 'Never married': 21},
    'Jewish': {'Now married': 56, 'Living with a partner': 6, 'Divorced': 6, 'Widowed': 9, 'Never married': 23},
    'Mormon': {'Now married': 66, 'Living with a partner': 7, 'Divorced': 12, 'Widowed': 5, 'Never married': 19},
    'Muslim': {'Now married': 41, 'Living with a partner': 8, 'Divorced': 9, 'Widowed': 6, 'Never married': 36},
    'Evangelical Protestant': {'Now married': 56, 'Living with a partner': 14, 'Divorced': 8, 'Widowed': 8, 'Never married': 18},
    'Mainline Protestant': {'Now married': 55, 'Living with a partner': 6, 'Divorced': 12, 'Widowed': 9, 'Never married': 18},
    'Unaffiliated': {'Now married': 37, 'Living with a partner': 11, 'Divorced': 11, 'Widowed': 7, 'Never married': 37},
    'Hindu': {'Now married': 60, 'Living with a partner': 0, 'Divorced': 2, 'Widowed': 1, 'Never married': 37},
    'Orthodox Christian': {'Now married': 48, 'Living with a partner': 5, 'Divorced': 9, 'Widowed': 6, 'Never married': 31}
}

religion_edu_stats = {
    'Buddhist': {'Less than HS': 20, 'HS Grad': 33, 'Some college': 28, 'College grad': 20, 'Postgraduate': 20},
    'Jehovah\'s Witness': {'Less than HS': 63, 'HS Grad': 25, 'Some college': 9, 'College grad': 3, 'Postgraduate': 9},
    'Jewish': {'Less than HS': 19, 'HS Grad': 22, 'Some college': 29, 'College grad': 31, 'Postgraduate': 31},
    'Mormon': {'Less than HS': 27, 'HS Grad': 40, 'Some college': 23, 'College grad': 10, 'Postgraduate': 10},
    'Muslim': {'Less than HS': 36, 'HS Grad': 25, 'Some college': 23, 'College grad': 17, 'Postgraduate': 17},
    'Evangelical Protestant': {'Less than HS': 43, 'HS Grad': 35, 'Some college': 14, 'College grad': 7, 'Postgraduate': 7},
    'Mainline Protestant': {'Less than HS': 37, 'HS Grad': 30, 'Some college': 19, 'College grad': 14, 'Postgraduate': 14},
    'Unaffiliated': {'Less than HS': 38, 'HS Grad': 32, 'Some college': 18, 'College grad': 11, 'Postgraduate': 11},
    'Hindu': {'Less than HS': 12, 'HS Grad': 11, 'Some college': 29, 'College grad': 48, 'Postgraduate': 48},
    'Orthodox Christian': {'Less than HS': 27, 'HS Grad': 34, 'Some college': 21, 'College grad': 18, 'Postgraduate': 18}
}

# All possible religions
all_religions = list(religion_race_stats.keys())

def calculate_combined_probability(row, religion):
    race = row['RACETHN']
    age = row['AGE']
    gender = row['GENDER']
    marital_status = row['MARITAL_ACS']
    education = row['EDUCCAT5']

    # Determine age group
    if 18 <= age <= 29:
        age_group = '18-29'
    elif 30 <= age <= 49:
        age_group = '30-49'
    elif 50 <= age <= 64:
        age_group = '50-64'
    else:
        age_group = '65-100'

    # Calculate probabilities
    race_prob = religion_race_stats.get(religion, {}).get(race, 1) / 100
    age_prob = religion_age_stats.get(religion, {}).get(age_group, 1) / 100
    gender_prob = religion_gender_stats.get(religion, {}).get(gender, 1) / 100
    marital_prob = religion_marital_stats.get(religion, {}).get(marital_status, 1) / 100
    edu_prob = religion_edu_stats.get(religion, {}).get(education, 1) / 100

    # Combine probabilities
    return race_prob * age_prob * gender_prob * marital_prob * edu_prob

# Assign religions based on combined probabilities
def assign_religion(row):
    probabilities = [calculate_combined_probability(row, religion) for religion in all_religions]
    return random.choices(all_religions, weights=probabilities)[0]

pop_df['RELIGCAT'] = pop_df.apply(assign_religion, axis=1)

# Display the final religion distribution
pop_df['RELIGCAT'].value_counts()

religion_count_by_race = pop_df.groupby(['RACETHN', 'RELIGCAT']).size().reset_index(name='Count')

print(religion_count_by_race)

pop_df.tail()

pop_df.head()

pop_df.isnull().sum()

"""#Credit Card numbers

Need to remove for certain people
"""

pip install Faker

pop_df['RACETHN'].unique()

"""Source: Feds paper: [link text](https://www.federalreserve.gov/publications/files/2021-report-economic-well-being-us-households-202205.pdf)"""

from faker import Faker
import pandas as pd
import random

fake = Faker()

# Define the percentages of individuals having credit cards for each racial group
credit_card_percentages = {
    'White non-Hispanic': 88,
    'Black non-Hispanic': 72,
    'Hispanic': 77,
    'Asian': 93,
    'Other race': 93
}

pop_df['RACETHN'] = pop_df['RACETHN'].astype(str)

def generate_credit_card_number(race):
    selected_percentage = credit_card_percentages[race]

    if random.randint(0, 100) <= selected_percentage:
        return fake.credit_card_number(card_type='mastercard')
    else:
        return 0  # For individuals without credit cards

# Generate credit card numbers based on racial groups and add them as a new column 'CC_NUM' in pop_df
pop_df['CC_NUM'] = pop_df['RACETHN'].apply(generate_credit_card_number)

pop_df.head()

# Grouping the DataFrame by 'RACETHN' and counting the non-null values in 'CC_NUM'
cc_num_count_per_race = pop_df.groupby('RACETHN')['CC_NUM'].apply(lambda x: x.notnull().sum()).reset_index(name='CreditCardCount')

# Displaying the count of credit card numbers per racial group
print(cc_num_count_per_race)

pop_df['cc_encoded'] = (pop_df['CC_NUM'] != 0).astype(int)

import numpy as np

# Add a column 'cc_disclosed' based on the condition that only those with a credit card (cc_encoded = 1) can disclose it
pop_df['cc_disclosed'] = np.where(
    pop_df['cc_encoded'] == 1,  # Only for individuals with a credit card
    np.random.choice([0, 1], size=pop_df.shape[0], p=[0.5, 0.5]),  # 50% chance to disclose
    0  # For those without a credit card, disclosure is 0
)

# Display the first few rows to verify the result
print(pop_df[['RACETHN', 'CC_NUM', 'cc_encoded', 'cc_disclosed']].head())

"""Names"""

pip install ArabicNames

from faker import Faker
import pandas as pd
import ArabicNames

# Initialize Faker
us = Faker('en_US')
es = Faker('es_ES')
ind = Faker('en_IN')
ch = Faker('zh_CN')
fake = Faker()

# Function to generate Indian name
def generate_indian_name_w():
    ind.seed_locale('en_IN')  # For Indian names
    return ind.name_female()

# Function to generate Chinese name
def generate_chinese_name_w():
    ch.seed_locale('zh_CN')  # For Chinese names
    return ch.romanized_name()

def generate_random_name_w():
    return fake.name_female()

# Function to generate Indian name
def generate_indian_name_m():
    ind.seed_locale('en_IN')  # For Indian names
    return ind.name_male()

# Function to generate Chinese name
def generate_chinese_name_m():
    ch.seed_locale('zh_CN')  # For Chinese names
    return ch.romanized_name()

def generate_random_name_m():
    return fake.name_male()

# Function to generate Indian name
def generate_indian_name_n():
    ind.seed_locale('en_IN')  # For Indian names
    return ind.name_nonbinary()

# Function to generate Chinese name
def generate_chinese_name_n():
    ch.seed_locale('zh_CN')  # For Chinese names
    return ch.romanized_name()

def generate_random_name_n():
    return fake.name_nonbinary()

# Function to generate first names based on gender and race
def generate_name(gender, race, religion):
    if gender == 'Male':
        if race == 'White non-Hispanic':

            if religion == 'Muslim':
                return ArabicNames.get_full_name()

            us.seed_locale('en_US')
            return us.name_male()
        elif race == 'Black non-Hispanic':

            if religion == 'Muslim':
                return ArabicNames.get_full_name()

            us.seed_locale('en_US')
            return us.name_male()
        elif race == 'Asian':

            # Define probabilities for male Asian names
            indian_prob = 21  # Probability percentage for Indian names
            chinese_prob = 24  # Probability percentage for Chinese names

            rand_num = random.randint(1, 100)  # Generate a random number between 1-100
            if religion == 'Hindu':
                return generate_indian_name_m()
            elif rand_num <= indian_prob:
                return generate_indian_name_m()
            elif rand_num <= (indian_prob + chinese_prob):
                return generate_chinese_name_m()
            else:
                return generate_random_name_m()  # For example, random name for the rest
        elif race == 'Hispanic':
            es.seed_locale('es_ES')  # For Spanish names
            return es.name_male()
        else:
            return fake.name_male()  # Handle other races as needed

    elif gender == 'Female':  # Female
        if race == 'White non-Hispanic':
            us.seed_locale('en_US')
            return us.name_female()
        elif race == 'Black non-Hispanic':
            us.seed_locale('en_US')
            return us.name_female()
        elif race == 'Asian':

            # Define probabilities for male Asian names
            indian_prob = 21  # Probability percentage for Indian names
            chinese_prob = 24  # Probability percentage for Chinese names

            rand_num = random.randint(1, 100)  # Generate a random number between 1-100

            if religion == 'Hindu':
                return generate_indian_name_m()
            elif rand_num <= indian_prob:
                return generate_indian_name_m()
            elif rand_num <= (indian_prob + chinese_prob):
                return generate_chinese_name_w()
            else:
                return generate_random_name_w()  # For example, random name for the rest
        elif race == 'Hispanic':
            es.seed_locale('es_ES')  # For Spanish names
            return es.name_female()
        else:
            return fake.name_female()  # Handle other races as needed

    else:
          if race == 'White non-Hispanic':

              if religion == 'Muslim':
                return ArabicNames.get_full_name()

              us.seed_locale('en_US')
              return us.name_nonbinary()

          elif race == 'Black non-Hispanic':

              if religion == 'Muslim':
                return ArabicNames.get_full_name()

              us.seed_locale('en_US')
              return us.name_nonbinary()
          elif race == 'Asian':

              # Define probabilities for male Asian names
              indian_prob = 21  # Probability percentage for Indian names
              chinese_prob = 24  # Probability percentage for Chinese names

              rand_num = random.randint(1, 100)  # Generate a random number between 1-100

              if rand_num <= indian_prob:
                  return generate_indian_name_n()
              elif rand_num <= (indian_prob + chinese_prob):
                  return generate_chinese_name_n()
              else:
                  return generate_random_name_n()  # For example, random name for the rest
          elif race == 'Hispanic':
              es.seed_locale('es_ES')  # For Spanish names
              return es.name_nonbinary
          else:
              return fake.name_nonbinary  # Handle other races as needed

# Generate first names based on gender and race
pop_df['NAME'] = [generate_name(g, r, z) for g, r, z in zip(pop_df['GENDER'], pop_df['RACETHN'], pop_df['RELIGCAT'])]

pop_df = pop_df[['NAME'] + [col for col in pop_df if col not in ['NAME']]]

pop_df.head()

pop_df.tail()

"""# Illnesses

Using race, gender, age statistics from [the CDC](https://www.cdc.gov/pcd/issues/2020/20_0130.htm#T1_down)
"""

import random

race_prob = {
    'Black non-Hispanic': {'0': 47.6, '1': 25.4, '2+': 27.0},
    'Hispanic': {'0': 61.5, '1': 20.8, '2+': 17.7},
    'Other race': {'0': 62.0, '1': 21.6, '2+': 16.4},
    'White non-Hispanic': {'0': 43.8, '1': 25.6, '2+': 30.6},
    'Asian': {'0': 62.0, '1': 21.6, '2+': 16.4}
}

gender_prob = {'Female': 46.7, 'Male': 49.8}

# Declaration: the original data from the website shows no less than 65 without upper limit as the last interval. Setting 100 as upper bound here is for dataset fit purpose.
age_prob = {'18-44': 72.6, '45-64': 36.6, '65-100': 12.4}

def get_age_group(age):
    if 18 <= age <= 44:
        return '18-44'
    elif 45 <= age <= 64:
        return '45-64'
    elif 65 <= age <= 100:
        return '65-100'
    else:
        return None

def assign_chronic_conditions(row):
    race_ethn = row['RACETHN']
    gender = row['GENDER']
    age = row['AGE']

    age_group = get_age_group(age)

    probability_0 = race_prob[race_ethn]['0'] * gender_prob[gender] * age_prob[age_group] / 100**2
    probability_1 = race_prob[race_ethn]['1'] * gender_prob[gender] * age_prob[age_group] / 100**2
    probability_2_plus = race_prob[race_ethn]['2+'] * gender_prob[gender] * age_prob[age_group] / 100**2

    total_prob = probability_0 + probability_1 + probability_2_plus
    probability_0 = (probability_0 / total_prob) * 100
    probability_1 = (probability_1 / total_prob) * 100
    probability_2_plus = (probability_2_plus / total_prob) * 100

    random_value = random.uniform(0, 100)
    if random_value < probability_0:
        return 0
    elif random_value < (probability_0 + probability_1):
        return 1
    else:
        return 2

# Apply the function to create the new column 'NumChronicIllness' based on race, gender, and age probabilities
pop_df['NumChronicIllness'] = pop_df.apply(assign_chronic_conditions, axis=1)

pop_df.tail()

pop_df.head()

chronic_illness_counts = pop_df['NumChronicIllness'].value_counts()

print(chronic_illness_counts)

"""#Imputations

Source: [Non-response rates for census](https://www.census.gov/newsroom/blogs/random-samplings/2021/08/2020-census-operational-quality-metrics-item-nonresponse-rates.html)

Using census values for age.
"""

import pandas as pd
import numpy as np
# Assuming pop_df is your DataFrame containing the AGE column

# Calculate the percentage of missing values in the AGE column

missing_percentage = 5.95

# Generate confidence levels based on whether the value is imputed or not for AGE column
def generate_confidence(is_imputed):
    if is_imputed == 1:
        return np.random.uniform(0, 100)  # Random value between 0 and 100 for imputed values
    else:
        return np.random.uniform(70, 100)  # Random value between 70 and 100 for non-imputed values

def generate_imputation(df, column):
    imputed_values = np.random.choice(df[column].dropna().index, size=int(df[column].notnull().sum() * (missing_percentage / 100)), replace=False)
    df['IMPUTED_' + column] = 0
    df.loc[imputed_values, 'IMPUTED_' + column] = 1
    df['CONFIDENCE_LEVEL_' + column] = df['IMPUTED_' + column].apply(lambda x: generate_confidence(x))

# Call function for 'AGE' column
generate_imputation(pop_df, 'AGE')

"""Using census values for race."""

# Calculate the percentage of missing values in the RACETHN column
missing_percentage_racethn = 5.77  # Given percentage of imputed data for RACETHN (5.77%)

# Generate confidence levels based on whether the value is imputed or not for AGE column
def generate_confidence(is_imputed):
    if is_imputed == 1:
        return np.random.uniform(0, 100)  # Random value between 0 and 100 for imputed values
    else:
        return np.random.uniform(70, 100)  # Random value between 70 and 100 for non-imputed values

def generate_imputation(df, column):
    imputed_values = np.random.choice(df[column].dropna().index, size=int(df[column].notnull().sum() * (missing_percentage / 100)), replace=False)
    df['IMPUTED_' + column] = 0
    df.loc[imputed_values, 'IMPUTED_' + column] = 1
    df['CONFIDENCE_LEVEL_' + column] = df['IMPUTED_' + column].apply(lambda x: generate_confidence(x))

# Call function for 'AGE' column
generate_imputation(pop_df, 'RACETHN')

import pandas as pd
import numpy as np

# Assuming pop_df is your DataFrame containing multiple columns

# List of columns (excluding AGE and RACETHN)
excluded_terms = ['age', 'race']  # Words to exclude from column selection
columns_to_impute = [col for col in pop_df.columns if not any(term in col.lower() for term in excluded_terms)]

# Generate random missing percentages for each column
missing_percentages = {col: np.random.uniform(5.1, 6.0) for col in columns_to_impute}
# Function to generate confidence levels

def generate_confidence(is_imputed):
    if is_imputed:
        return np.random.uniform(0, 100)  # Random value between 0 and 100 for imputed values
    else:
        return np.random.uniform(70, 100)  # Random value between 70 and 100 for non-imputed values

def generate_imputation(df, column, missing_percentage):
    imputed_values = np.random.choice(df[column].dropna().index, size=int(df[column].notnull().sum() * (missing_percentage / 100)), replace=False)
    df['IMPUTED_' + column] = 0
    df.loc[imputed_values, 'IMPUTED_' + column] = 1
    df['CONFIDENCE_LEVEL_' + column] = df['IMPUTED_' + column].apply(lambda x: generate_confidence(x))

# Loop through each column and create corresponding 'IMPUTED' and 'CONFIDENCE_LEVEL' columns
for col in columns_to_impute:
    generate_imputation(pop_df, col, missing_percentages[col])

#pop_df.to_csv('synthetic_population_dataset.csv')

pop_df.head()

def label_confidence_intervals(row):
    for col in row.index:
        if col.startswith('CONFIDENCE_LEVEL_'):
            ci_value = row[col]
            attribute_name = col.replace('CONFIDENCE_LEVEL_', '')  # Extracting attribute name
            label = ""
            if ci_value >= 90:
                label = "is"
            elif 75 <= ci_value < 90:
                label = "is probably"
            elif 35 <= ci_value < 75:
                label = "is possibly"
            elif 10 <= ci_value < 35:
                label = "is unlikely but might be"
            elif ci_value < 10:
                label = "is not"

            label_col_name = f"CI_LABEL_{attribute_name}"  # Constructing new column name
            row[label_col_name] = label  # Assigning label to the new column for this row
    return row

# Apply the labeling function to each row
pop_df = pop_df.apply(label_confidence_intervals, axis=1)

pop_df.head()

# Assuming pop_df is your DataFrame and 'AGE' is the column with age values
age_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120] # Note that the bins go up to the next integer
age_labels = ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80-89', '90-99', '100-109', '110-119']
pop_df['AGE_INT'] = pd.cut(pop_df['AGE'], bins=age_bins, labels=age_labels, right=False)

pop_df.head()

pop_df.to_csv('synthetic_population_dataset.csv')
