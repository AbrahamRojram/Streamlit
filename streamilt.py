import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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
    
    selected_game_type = st.sidebar.radio("Select Game Type", game_type_options)

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
        elif 'score1' in filtered_df.columns and 'score2' in filtered_df.columns:
            # Create game result based on scores
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
            # Create new dataframes for plotting
            wins_df = filtered_df[filtered_df['game_result'] == 'W'].copy()
            losses_df = filtered_df[filtered_df['game_result'] == 'L'].copy()
            
            # Calculate cumulative counts
            if not wins_df.empty:
                wins_df = wins_df.sort_values('game_number')
                wins_df['cumulative_wins'] = range(1, len(wins_df) + 1)
                wins_data = pd.DataFrame({
                    'Game Number': wins_df['game_number'],
                    'Count': wins_df['cumulative_wins'],
                    'Type': ['Wins'] * len(wins_df)
                })
            else:
                wins_data = pd.DataFrame(columns=['Game Number', 'Count', 'Type'])
            
            if not losses_df.empty:
                losses_df = losses_df.sort_values('game_number')
                losses_df['cumulative_losses'] = range(1, len(losses_df) + 1)
                losses_data = pd.DataFrame({
                    'Game Number': losses_df['game_number'],
                    'Count': losses_df['cumulative_losses'],
                    'Type': ['Losses'] * len(losses_df)
                })
            else:
                losses_data = pd.DataFrame(columns=['Game Number', 'Count', 'Type'])
            
            # Combine for Altair
            plot_data = pd.concat([wins_data, losses_data])
            
            if not plot_data.empty:
                # Create Altair chart
                chart = alt.Chart(plot_data).mark_line(point=True).encode(
                    x='Game Number:Q',
                    y='Count:Q',
                    color=alt.Color('Type:N', scale=alt.Scale(domain=['Wins', 'Losses'], range=['green', 'red'])),
                    tooltip=['Game Number', 'Count', 'Type']
                ).properties(
                    width=600,
                    height=400
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("No game results available to plot.")
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
                # Create data for pie chart
                pie_data = pd.DataFrame({
                    'Category': ['Wins', 'Losses'],
                    'Value': [win_count, loss_count]
                })
                
                # Create pie chart with Altair
                pie_chart = alt.Chart(pie_data).mark_arc().encode(
                    theta=alt.Theta(field="Value", type="quantitative"),
                    color=alt.Color(field="Category", type="nominal", 
                                    scale=alt.Scale(domain=['Wins', 'Losses'], range=['green', 'red'])),
                    tooltip=['Category', 'Value']
                ).properties(
                    width=250,
                    height=250
                )
                
                st.altair_chart(pie_chart, use_container_width=True)
                
                # Show the actual numbers
                st.metric("Total Games", total_games)
                col_win, col_loss = st.columns(2)
                with col_win:
                    st.metric("Wins", win_count)
                    st.metric("Win %", f"{(win_count/total_games*100):.1f}%")
                with col_loss:
                    st.metric("Losses", loss_count)
                    st.metric("Loss %", f"{(loss_count/total_games*100):.1f}%")
            else:
                st.write("No games with clear results found for the selected filters.")
        else:
            st.write("No data available for the selected filters or unable to determine game results.")

    # Footer with information
    st.markdown("---")
    st.info("NBA Dashboard displaying data from nba_all_elo.csv")
else:
    st.error("Unable to load data. Please check that the file exists and is properly formatted.")