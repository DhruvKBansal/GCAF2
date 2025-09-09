import pandas as pd
import os
import glob
from datetime import datetime
try:
    from git import Repo, GitCommandError
except ImportError:
    print("GitPython is not installed. Please install it using: pip install GitPython")
    exit()


def delete_file_from_github(repo_path, filename_to_delete, commit_message):
    """
    Deletes a specific file from the local repository and pushes the deletion to GitHub.
    """
    try:
        repo = Repo(repo_path)
        file_path_in_repo = os.path.join(repo_path, filename_to_delete)

        if os.path.exists(file_path_in_repo):
            print(f"Deleting {filename_to_delete} from the repository...")
            repo.index.remove([file_path_in_repo], working_tree=True)
            repo.index.commit(commit_message)
            
            origin = repo.remotes.origin
            origin.push()
            print(f"Successfully pushed the deletion of {filename_to_delete} to GitHub.")
        else:
            print(f"{filename_to_delete} not found locally. It might have been deleted already.")

    except GitCommandError as e:
        if f"pathspec '{os.path.join(repo_path, filename_to_delete)}' did not match any files" in str(e):
            print(f"{filename_to_delete} is not tracked by Git. No need to remove.")
        else:
            print(f"A Git error occurred during deletion: {e}")
    except Exception as e:
        print(f"An error occurred during the Git deletion operation: {e}")


def commit_and_push_to_github(repo_path, commit_message):
    """
    Commits and pushes the leaderboard.csv file.
    """
    try:
        repo = Repo(repo_path)
        file_path = 'leaderboard.csv'
        origin = repo.remotes.origin
        
        print(f"Adding and committing {file_path}...")
        repo.index.add([file_path])
        repo.index.commit(commit_message)
        
        print("Pushing changes to GitHub...")
        origin.push()
        print("Successfully pushed leaderboard to GitHub.")

    except GitCommandError as e:
        print(f"A Git error occurred: {e}")
        print("If you see a 'failed to push some refs' error, try running 'git pull' in your terminal first.")
    except Exception as e:
        print(f"An error occurred during the Git operation: {e}")


def process_arcade_report(input_folder, output_filename, repo_path):
    # Processes the latest report, saves it as a clean CSV file, and triggers a GitHub push.
    try:
        search_pattern = os.path.join(input_folder, 'GCAF*.csv')
        files = glob.glob(search_pattern)
        if not files:
            print(f"Error: No report files found in '{input_folder}'.")
            return

        latest_file = max(files, key=os.path.getctime)
        print(f"Processing the latest report: {os.path.basename(latest_file)}")
        df = pd.read_csv(latest_file)

        # 1. Define columns to drop, keeping necessary ones for calculation
        columns_to_drop = [
            'User Email', 'Google Cloud Skills Boost Profile URL',
            'Names of Completed Skill Badges', 
            'Names of Completed Trivia Games', 'Names of Completed Lab-free Courses',
            'Profile URL Status'
        ]
        columns_to_drop_existing = [col for col in columns_to_drop if col in df.columns]
        df_modified = df.drop(columns=columns_to_drop_existing)

        # 2. Calculate points
        df_modified['# of Skill Badges Completed'] = pd.to_numeric(df_modified['# of Skill Badges Completed'], errors='coerce').fillna(0)
        df_modified['# of Arcade Games Completed'] = pd.to_numeric(df_modified['# of Arcade Games Completed'], errors='coerce').fillna(0)
        df_modified['# of Trivia Games Completed'] = pd.to_numeric(df_modified['# of Trivia Games Completed'], errors='coerce').fillna(0)
        
        # Base points calculation
        df_modified['Points'] = (df_modified['# of Skill Badges Completed'] / 2) + \
                                df_modified['# of Arcade Games Completed'] + \
                                df_modified['# of Trivia Games Completed']

        # Add bonus point for the "Future Ready Skills [Game]"
        if 'Names of Completed Arcade Games' in df_modified.columns:
            df_modified['Names of Completed Arcade Games'] = df_modified['Names of Completed Arcade Games'].fillna('')
            bonus_points_game = df_modified['Names of Completed Arcade Games'].str.contains("Future Ready Skills [Game]", na=False, regex=False).astype(int)
            df_modified['Points'] += bonus_points_game

        # Add bonus points for Milestones
        if 'Milestone Earned' in df_modified.columns:
            milestone_points_map = {
                'Milestone 1': 2,
                'Milestone 2': 8,
                'Milestone 3': 15,
                'Milestone 4': 25
            }
            df_modified['Milestone Earned'] = df_modified['Milestone Earned'].fillna('None')
            bonus_points_milestone = df_modified['Milestone Earned'].map(milestone_points_map).fillna(0)
            df_modified['Points'] += bonus_points_milestone
        
        # Now we can drop the temporary columns used for calculation
        final_drop_columns = ['Names of Completed Arcade Games'] # Keep 'Milestone Earned'
        final_drop_columns_existing = [col for col in final_drop_columns if col in df_modified.columns]
        df_modified = df_modified.drop(columns=final_drop_columns_existing)

        # 3. Sort by Points
        df_sorted = df_modified.sort_values(by='Points', ascending=False)

        # 4. Reorder columns
        all_cols = df_sorted.columns.tolist()
        if 'User Name' in all_cols and 'Points' in all_cols and 'Milestone Earned' in all_cols and 'Access Code Redemption Status' in all_cols:
            all_cols.remove('User Name')
            all_cols.remove('Points')
            all_cols.remove('Milestone Earned')
            all_cols.remove('Access Code Redemption Status')
            new_order = ['User Name', 'Points', 'Milestone Earned'] + all_cols + ['Access Code Redemption Status']
            df_reordered = df_sorted[new_order]
        else:
            df_reordered = df_sorted

        # 5. Save the processed file as a clean CSV
        output_path = os.path.join(repo_path, output_filename)
        df_reordered.to_csv(output_path, index=False)
        print(f"Successfully processed the report. Sorted file saved as: {output_path}")

        # 6. Commit and Push to GitHub
        today_date = datetime.now().strftime("%d %B %Y")
        commit_msg = f"Leaderboard updated for {today_date}"
        commit_and_push_to_github(repo_path, commit_msg)
    except Exception as e:
        print(f"An error occurred during report processing: {e}")


if __name__ == '__main__':
    local_repo_path = '.' 
    input_reports_folder = os.path.join(local_repo_path, 'daily_reports')
    output_leaderboard_file = 'leaderboard.csv' 
    
    if not os.path.exists(input_reports_folder):
        os.makedirs(input_reports_folder)
        
    process_arcade_report(input_reports_folder, output_leaderboard_file, local_repo_path)

