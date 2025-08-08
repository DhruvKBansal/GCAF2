import pandas as pd
import os
import glob
from datetime import datetime
# You must install this library first: pip install GitPython
try:
    from git import Repo, GitCommandError
except ImportError:
    print("GitPython is not installed. Please install it using: pip install GitPython")
    exit()


def commit_and_push_to_github(repo_path, commit_message):
    """
    Commits and pushes the leaderboard.csv file to a GitHub repository.

    Args:
        repo_path (str): The local path to the git repository.
        commit_message (str): The message for the commit.
    """
    try:
        repo = Repo(repo_path)
        
        # Define the path for the leaderboard file
        file_path = 'leaderboard.csv'

        # Check for changes, including untracked files
        if repo.is_dirty(untracked_files=True, path=file_path):
            print(f"Changes detected in {file_path}. Committing and pushing...")
            repo.index.add([file_path])
            repo.index.commit(commit_message)
            
            origin = repo.remotes.origin
            origin.push()
            print("Successfully pushed leaderboard to GitHub.")
        else:
            print(f"No changes in {file_path} to commit.")

    except GitCommandError as e:
        print(f"A Git error occurred: {e}")
    except Exception as e:
        print(f"An error occurred during the Git operation: {e}")


def process_arcade_report(input_folder, output_filename, repo_path):
    """
    Processes the latest report, saves it as a clean CSV file, 
    and triggers a GitHub push.
    """
    try:
        # Find the latest report file
        search_pattern = os.path.join(input_folder, 'GCAF*.csv')
        files = glob.glob(search_pattern)
        if not files:
            print(f"Error: No report files found in '{input_folder}'.")
            return

        latest_file = max(files, key=os.path.getctime)
        print(f"Processing the latest report: {os.path.basename(latest_file)}")

        df = pd.read_csv(latest_file)

        # 1. Remove specified columns
        columns_to_drop = [
            'User Email', 'Google Cloud Skills Boost Profile URL',
            'Names of Completed Skill Badges', 'Names of Completed Arcade Games',
            'Names of Completed Trivia Games', 'Names of Completed Lab-free Courses',
            'Profile URL Status', 'Access Code Redemption Status'
        ]
        columns_to_drop_existing = [col for col in columns_to_drop if col in df.columns]
        df_modified = df.drop(columns=columns_to_drop_existing)

        # 2. Calculate points (allowing for 0.5 points)
        df_modified['# of Skill Badges Completed'] = pd.to_numeric(df_modified['# of Skill Badges Completed'], errors='coerce').fillna(0)
        df_modified['# of Arcade Games Completed'] = pd.to_numeric(df_modified['# of Arcade Games Completed'], errors='coerce').fillna(0)
        df_modified['# of Trivia Games Completed'] = pd.to_numeric(df_modified['# of Trivia Games Completed'], errors='coerce').fillna(0)
        
        df_modified['Points'] = (df_modified['# of Skill Badges Completed'] / 2) + \
                                df_modified['# of Arcade Games Completed'] + \
                                df_modified['# of Trivia Games Completed']

        # 3. Sort by Points
        df_sorted = df_modified.sort_values(by='Points', ascending=False)

        # 4. Reorder columns
        all_cols = df_sorted.columns.tolist()
        if 'User Name' in all_cols and 'Points' in all_cols:
            all_cols.remove('User Name')
            all_cols.remove('Points')
            new_order = ['User Name', 'Points'] + all_cols
            df_reordered = df_sorted[new_order]
        else:
            df_reordered = df_sorted

        # 5. Save the processed file as a clean CSV
        output_path = os.path.join(repo_path, output_filename)
        df_reordered.to_csv(output_path, index=False)
        
        print(f"Successfully processed the report. Sorted file saved as: {output_path}")

        # 6. Commit and Push to GitHub
        today_date = datetime.now().strftime("%d %B %Y")
        commit_msg = f"Update leaderboard for {today_date}"
        commit_and_push_to_github(repo_path, commit_msg)

    except Exception as e:
        print(f"An error occurred during report processing: {e}")

# --- How to use the final script ---
if __name__ == '__main__':
    local_repo_path = '.' 

    input_reports_folder = os.path.join(local_repo_path, 'daily_reports')
    
    # The output filename is a CSV file
    output_leaderboard_file = 'leaderboard.csv' 
    
    if not os.path.exists(input_reports_folder):
        os.makedirs(input_reports_folder)
        
    process_arcade_report(input_reports_folder, output_leaderboard_file, local_repo_path)
