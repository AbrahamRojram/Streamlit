import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
from matplotlib.ticker import MaxNLocator

# Set page configuration
st.set_page_config(
    page_title="NBA Dashboard",
    layout="wide"
)

# Set Matplotlib style
plt.style.use('ggplot')

# Page title
st.title("NBA Dashboard")

# Load data
@st.cache_data
def load_data():
    # Load the NBA dataset
    df = pd.read_csv('nba_all_elo.csv')
    return df

# Load the data
try:
    df = load_data()
    data_loaded = True
    
    # Debug info - display column names
    st.sidebar.expander("Debug - Column Names").write(df.columns.tolist())
    
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.error("Make sure the file 'nba_all_elo.csv' is in the same directory as this app.")
    data_loaded = False

if data_loaded:
    # Sidebar
    st.sidebar.header("Filters")

    # Year selector - Use 'year_id' column
    years = sorted(df['year_id'].unique().tolist())
    selected_year = st.sidebar.selectbox("Select Year", years)

    # Team selector - using fran_id as the team identifier
    # Get unique team names from both team and opponent columns
    teams = sorted(set(df['fran_id'].unique()) | set(df['opp_fran'].unique()))
    selected_team = st.sidebar.selectbox("Select Team", teams)

    # Game type selector (Regular/Playoff/Both)
    game_type_options = ["Regular Season", "Playoffs", "Both"]
    selected_game_type = st.sidebar.radio("Select Game Type", game_type_options, key="game_type")

    # Filter data based on selections
    # First, filter by year
    year_filter = df['year_id'] == selected_year
    
    # Then filter for games involving the selected team (either as team or opponent)
    team_filter = (df['fran_id'] == selected_team) | (df['opp_fran'] == selected_team)
    
    # Combine filters
    filtered_df = df[year_filter & team_filter].copy()
    
    # Filter by game type if applicable
    if selected_game_type != "Both":
        if selected_game_type == "Playoffs":
            filtered_df = filtered_df[filtered_df['is_playoffs'] == 1]
        else:  # Regular Season
            filtered_df = filtered_df[filtered_df['is_playoffs'] == 0]
    
    # Sort data by date for proper cumulative calculation
    if 'date_game' in filtered_df.columns:
        filtered_df['date_game'] = pd.to_datetime(filtered_df['date_game'])
        filtered_df = filtered_df.sort_values('date_game')
    
    # Determine if selected team won or lost each game
    filtered_df['is_team'] = filtered_df['fran_id'] == selected_team
    filtered_df['team_result'] = filtered_df.apply(
        lambda row: row['game_result'] if row['is_team'] else 
                    ('W' if row['game_result'] == 'L' else 'L'), 
        axis=1
    )
    
    # Add a game counter column
    filtered_df = filtered_df.reset_index(drop=True)
    filtered_df['game_number'] = range(1, len(filtered_df) + 1)
    
    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Line chart for cumulative wins and losses using Matplotlib
        st.subheader(f"Cumulative Wins and Losses for {selected_team} ({selected_year})")
        
        if not filtered_df.empty:
            # Calculate cumulative wins and losses
            wins_df = filtered_df[filtered_df['team_result'] == 'W'].copy()
            losses_df = filtered_df[filtered_df['team_result'] == 'L'].copy()
            
            # Create a Matplotlib figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot cumulative wins
            if not wins_df.empty:
                wins_df = wins_df.sort_values('game_number')
                wins_df['cumulative_wins'] = range(1, len(wins_df) + 1)
                ax.plot(wins_df['game_number'], wins_df['cumulative_wins'], 
                        marker='o', linestyle='-', color='green', label='Wins')
            
            # Plot cumulative losses
            if not losses_df.empty:
                losses_df = losses_df.sort_values('game_number')
                losses_df['cumulative_losses'] = range(1, len(losses_df) + 1)
                ax.plot(losses_df['game_number'], losses_df['cumulative_losses'],
                        marker='o', linestyle='-', color='red', label='Losses')
            
            # Enhance the plot
            ax.set_xlabel('Game Number')
            ax.set_ylabel('Cumulative Count')
            ax.set_title(f'{selected_team} Win/Loss Progression ({selected_year})')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            
            # Display plot in Streamlit
            st.pyplot(fig)
            
            # Also provide the Altair chart for interactive features
            # Create dataframes for plotting with Altair
            if not wins_df.empty:
                wins_data = pd.DataFrame({
                    'Game Number': wins_df['game_number'],
                    'Count': wins_df['cumulative_wins'],
                    'Type': ['Wins'] * len(wins_df)
                })
            else:
                wins_data = pd.DataFrame(columns=['Game Number', 'Count', 'Type'])
            
            if not losses_df.empty:
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
                    height=300
                ).interactive()
                
                st.altair_chart(chart, use_container_width=True)
        else:
            st.write("No game data available for the selected filters.")

    with col2:
        # Pie chart for win/loss percentage using Matplotlib
        st.subheader(f"Win/Loss Distribution for {selected_team} ({selected_year})")
        
        if not filtered_df.empty:
            # Count wins and losses
            results_count = filtered_df['team_result'].value_counts()
            
            # Calculate percentages
            win_count = results_count.get('W', 0)
            loss_count = results_count.get('L', 0)
            total_games = win_count + loss_count
            
            if total_games > 0:
                # Create Matplotlib pie chart
                fig, ax = plt.subplots(figsize=(5, 5))
                
                labels = ['Wins', 'Losses']
                sizes = [win_count, loss_count]
                colors = ['green', 'red']
                explode = (0.1, 0)  # Explode the wins slice for emphasis
                
                ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                       autopct='%1.1f%%', shadow=True, startangle=90)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                ax.set_title(f'{selected_team} Win/Loss Percentage ({selected_year})')
                
                # Display in Streamlit
                st.pyplot(fig)
                
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
            st.write("No data available for the selected filters.")

    # Footer with information
    st.markdown("---")
    st.info("NBA Dashboard displaying data from nba_all_elo.csv")
else:
    st.error("Unable to load data. Please check that the file exists and is properly formatted.")