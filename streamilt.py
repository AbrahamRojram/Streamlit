import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="NBA Dashboard",
    layout="wide"
)

# Page title
st.title("NBA Dashboard")

# Load data
@st.cache_data
def load_data():
    # Load the NBA dataset
    df = pd.read_csv('nba_all_elo.csv')
    
    # Extract year from date (assuming date format is YYYY-MM-DD)
    if 'date' in df.columns:
        df['year'] = pd.to_datetime(df['date']).dt.year
    
    return df

# Load the data
try:
    df = load_data()
    data_loaded = True
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.error("Make sure the file 'nba_all_elo.csv' is in the same directory as this app.")
    data_loaded = False

if data_loaded:
    # Sidebar
    st.sidebar.header("Filters")

    # Year selector
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Select Year", years)

    # Team selector - assuming 'team1' and 'team2' are the team columns
    # Collect all unique team names from both columns
    if 'team1' in df.columns and 'team2' in df.columns:
        teams = sorted(set(df['team1'].unique()) | set(df['team2'].unique()))
    else:
        # Fallback if column names are different
        team_columns = [col for col in df.columns if 'team' in col.lower()]
        if team_columns:
            teams = sorted(pd.concat([df[col] for col in team_columns]).unique())
        else:
            st.error("Could not find team columns in the dataset.")
            teams = []
    
    selected_team = st.sidebar.selectbox("Select Team", teams)

    # Game type selector (Regular/Playoff/Both)
    # Check if there's a column indicating playoff status
    if 'is_playoffs' in df.columns:
        game_type_options = ["Regular", "Playoff", "Both"]
    else:
        # Try to find a column that might indicate game type
        playoff_columns = [col for col in df.columns if 'playoff' in col.lower() or 'season' in col.lower()]
        if playoff_columns:
            game_type_options = ["Regular", "Playoff", "Both"]
        else:
            # Default to both if we can't determine game types
            game_type_options = ["Both"]
            st.warning("Could not find playoff indicator column. Showing all games.")
    
    selected_game_type = st.sidebar.pills("Select Game Type", game_type_options)

    # Filter data based on selections
    # First, filter for games involving the selected team (either as team1 or team2)
    if 'team1' in df.columns and 'team2' in df.columns:
        team_filter = (df['team1'] == selected_team) | (df['team2'] == selected_team)
        filtered_df = df[team_filter & (df['year'] == selected_year)]
    else:
        # Fallback if column names are different
        st.error("Could not apply team filter due to missing team columns.")
        filtered_df = df[df['year'] == selected_year]

    # Filter by game type if applicable
    if 'is_playoffs' in df.columns and selected_game_type != "Both":
        if selected_game_type == "Playoff":
            filtered_df = filtered_df[filtered_df['is_playoffs'] == 1]
        else:  # Regular
            filtered_df = filtered_df[filtered_df['is_playoffs'] == 0]
    
    # Determine game results
    # Need to determine if the selected team won or lost each game
    if not filtered_df.empty:
        # Check for common result column patterns
        if 'game_result' in filtered_df.columns:
            # If there's a direct game_result column
            pass
        elif 'team1_score' in filtered_df.columns and 'team2_score' in filtered_df.columns:
            # Create game result based on scores
            filtered_df['game_result'] = filtered_df.apply(
                lambda row: 'W' if ((row['team1'] == selected_team and row['team1_score'] > row['team2_score']) or 
                                     (row['team2'] == selected_team and row['team2_score'] > row['team1_score'])) else 'L',
                axis=1
            )
        elif 'score1' in filtered_df.columns and 'score2' in filtered_df.columns:
            # Alternative column names for scores
            filtered_df['game_result'] = filtered_df.apply(
                lambda row: 'W' if ((row['team1'] == selected_team and row['score1'] > row['score2']) or 
                                     (row['team2'] == selected_team and row['score2'] > row['score1'])) else 'L',
                axis=1
            )
        else:
            # Look for other potential score columns
            score_cols = [col for col in filtered_df.columns if 'score' in col.lower()]
            if len(score_cols) >= 2:
                st.warning(f"Using score columns: {score_cols[:2]}. Results may not be accurate.")
                filtered_df['game_result'] = 'Unknown'  # Default fallback
            else:
                st.error("Could not determine game results due to missing score columns.")
                filtered_df['game_result'] = 'Unknown'  # Default fallback

    # Add a game counter column
    filtered_df = filtered_df.sort_values('date' if 'date' in filtered_df.columns else filtered_df.columns[0])
    filtered_df['game_number'] = range(1, len(filtered_df) + 1)

    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Line chart for cumulative wins and losses
        st.subheader(f"Cumulative Wins and Losses for {selected_team} ({selected_year})")
        
        # Calculate cumulative wins and losses
        if not filtered_df.empty and 'game_result' in filtered_df.columns:
            # Create a new dataframe for plotting
            wins_df = filtered_df[filtered_df['game_result'] == 'W'].copy()
            losses_df = filtered_df[filtered_df['game_result'] == 'L'].copy()
            
            # Calculate cumulative counts
            if not wins_df.empty:
                wins_df['cumulative_wins'] = range(1, len(wins_df) + 1)
            if not losses_df.empty:
                losses_df['cumulative_losses'] = range(1, len(losses_df) + 1)
            
            # Create a figure with wins and losses lines
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot cumulative wins and losses
            if not wins_df.empty:
                ax.plot(wins_df['game_number'], wins_df['cumulative_wins'], label='Wins', color='green', marker='o')
            
            if not losses_df.empty:
                ax.plot(losses_df['game_number'], losses_df['cumulative_losses'], label='Losses', color='red', marker='x')
            
            ax.set_xlabel('Game Number')
            ax.set_ylabel('Cumulative Count')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Display the plot
            st.pyplot(fig)
        else:
            st.write("No data available for the selected filters or unable to determine game results.")

    with col2:
        # Pie chart for win/loss percentage
        st.subheader(f"Win/Loss Distribution for {selected_team} ({selected_year})")
        
        if not filtered_df.empty and 'game_result' in filtered_df.columns:
            # Count wins and losses
            results_count = filtered_df['game_result'].value_counts()
            
            # Calculate percentages
            win_count = results_count.get('W', 0)
            loss_count = results_count.get('L', 0)
            total_games = win_count + loss_count
            
            if total_games > 0:
                # Create labels and values for the pie chart
                labels = ['Wins', 'Losses']
                values = [win_count, loss_count]
                
                # Create the pie chart
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=['green', 'red'])
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                
                # Display the pie chart
                st.pyplot(fig)
                
                # Show the actual numbers
                st.metric("Total Games", total_games)
                col_win, col_loss = st.columns(2)
                with col_win:
                    st.metric("Wins", win_count)
                with col_loss:
                    st.metric("Losses", loss_count)
            else:
                st.write("No games with clear results found for the selected filters.")
        else:
            st.write("No data available for the selected filters or unable to determine game results.")

    # Footer with information
    st.markdown("---")
    st.info("NBA Dashboard displaying data from nba_all_elo.csv")