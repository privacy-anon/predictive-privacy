import os
import glob
import re
import pandas as pd

# Folder with your CSV files
INPUT_DIR = "" # add path to your directory of responses here

# Final combined CSV output
OUTPUT_FILE = "survey2_results.csv"

# Define the set of normal question responses
VALID_Q_RESPONSES = {
    "Not at all harmful",
    "Slightly harmful",
    "Moderately harmful",
    "Very harmful",
    "Extremely harmful",
}

# Number of total questions per profile
NUM_QUESTIONS = 8


def parse_single_row(row_values, valid_responses, num_questions=8):
    """
    Expects a row in the following structure:
       [Timestamp, ProlificID, SyntheticID1, maybeAttnOrQ1, Q2..Q8, SyntheticID2, ...]
    In this scheme:
       - Column 0 is the Timestamp (ignored).
       - Column 1 is the ProlificID.
       - The remaining columns form repeated blocks for each synthetic profile.
    
    Each synthetic block is parsed as follows:
       - The first cell of the block is the SyntheticID.
       - The next cell is either:
         (a) A valid response (if it’s in valid_responses) representing Q1 (i.e., no attention check), or
         (b) An attention-check response (if not in valid_responses), followed by 8 cells for Q1..Q8.
       - In case (a), after using the second cell as Q1, the next 7 cells are taken as Q2..Q8.
    
    Returns a DataFrame with columns:
       [ProlificID, SyntheticPersonID, AttnCheck, Q1, Q2, ..., Q8]
    Raises ValueError if the row does not match the expected structure.
    """
    # Use the second column as the Prolific ID
    prolific_id = row_values[1]
    # Data blocks start from the third column
    data_blocks = row_values[2:]
    
    # Validate that we have a non-empty ProlificID.
    if pd.isna(prolific_id) or str(prolific_id).strip() == "":
        raise ValueError("Invalid or empty Prolific ID.")
    
    columns = ["ProlificID", "SyntheticPersonID", "AttnCheck"] + [f"Q{i+1}" for i in range(num_questions)]
    records = []
    i = 0
    while i < len(data_blocks):
        # 1) Synthetic ID for this block
        synthetic_id = data_blocks[i]
        i += 1
        if i >= len(data_blocks):
            raise ValueError(f"Row ended unexpectedly after Synthetic ID {synthetic_id}.")

        # 2) Look at the next cell: is it a valid answer (Q1) or an attention check?
        second_cell = data_blocks[i]
        if second_cell in valid_responses:
            # => No attention check for this block
            attn_check = None
            q_answers = [second_cell]  # Q1
            i += 1

            # Next 7 cells for Q2..Q8
            needed = num_questions - 1
            if i + needed > len(data_blocks):
                raise ValueError(
                    f"Not enough columns for Q2..Q{num_questions} after Q1 for SyntheticID={synthetic_id}"
                )
            q_answers.extend(data_blocks[i : i + needed])
            i += needed
        else:
            # => This cell is treated as the attention-check
            attn_check = second_cell
            i += 1  # consume the attention-check cell

            # Next 8 cells must be Q1..Q8
            if i + num_questions > len(data_blocks):
                raise ValueError(
                    f"Not enough columns for Q1..Q{num_questions} after attention-check for SyntheticID={synthetic_id}"
                )
            q_answers = data_blocks[i : i + num_questions]
            i += num_questions

        if len(q_answers) != num_questions:
            raise ValueError(
                f"Expected {num_questions} question answers, got {len(q_answers)} (SyntheticID={synthetic_id})."
            )
        # Build one record for this synthetic profile, with the same prolific id for all
        records.append([prolific_id, synthetic_id, attn_check] + q_answers)
    return pd.DataFrame(records, columns=columns)


def get_condition_from_filename(filepath):
    """
    Extracts a Q number from the file name and returns the condition.
    
    Ranges:
      Q1-Q19    -> "Control"
      Q20-Q38   -> "Health"
      Q39-Q57   -> "Financial"
      Q58-Q76   -> "Sensitive"
    If no Q number is found, returns "Unknown".
    """
    basename = os.path.basename(filepath)
    match = re.search(r'(\d+)', basename)
    if match:
        q_num = int(match.group(1))
        if 1 <= q_num <= 19:
            return "Control"
        elif 20 <= q_num <= 38:
            return "Health"
        elif 39 <= q_num <= 57:
            return "Control"
        elif 58 <= q_num <= 76:
            return "Health"
    return "Unknown"

def get_percentile_from_filename(filepath):
    """
    Extracts a Q number from the file name and returns the condition.
    
    Ranges:
      Q1-Q38   -> 50
      Q39-Q76  -> 75
    If no Q number is found, returns "Unknown".
    """
    basename = os.path.basename(filepath)
    match = re.search(r'(\d+)', basename)
    if match:
        q_num = int(match.group(1))
        if 1 <= q_num <= 38:
            return 50
        elif 39 <= q_num <= 76:
            return 75
    return "Unknown"


def reshape_file(filepath, valid_responses, num_questions=8):
    """
    Reads the CSV file, then loops over each row.
    Attempts to parse each row as participant data and skips any row that cannot be parsed.
    Adds a "Condition" column based on the file name.
    Returns a combined DataFrame of all valid rows from that file.
    """
    df = pd.read_csv(filepath, header=None)
    
    # Optionally, drop fully empty rows:
    df = df.dropna(how="all").reset_index(drop=True)
    
    df_parsed_list = []
    for i in range(len(df)):
        row = df.iloc[i].tolist()
        try:
            parsed = parse_single_row(row, valid_responses, num_questions=num_questions)
            df_parsed_list.append(parsed)
        except ValueError as e:
            # Likely a row with question text or incomplete data – skip it.
            print(f"Skipping row {i} in {filepath} due to parse error: {e}")
            continue
    
    if df_parsed_list:
        df_file = pd.concat(df_parsed_list, ignore_index=True)
        # Add condition column based on the file name.
        condition = get_condition_from_filename(filepath)
        df_file["Condition"] = condition
        percentile = get_percentile_from_filename(filepath)
        df_file["Certainty"] = percentile
        return df_file
    else:
        return None


def main():
    all_csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
    combined_list = []
    for csv_file in all_csv_files:
        df_reshaped = reshape_file(csv_file, VALID_Q_RESPONSES, num_questions=NUM_QUESTIONS)
        if df_reshaped is not None and not df_reshaped.empty:
            combined_list.append(df_reshaped)
    
    if combined_list:
        final_df = pd.concat(combined_list, ignore_index=True)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved combined, reshaped CSV to {OUTPUT_FILE}")
    else:
        print("No valid data to write.")


if __name__ == "__main__":
    main()
