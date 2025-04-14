import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from datetime import datetime, timedelta

# Check if running in Streamlit Cloud
if 'connections' not in st.secrets:
    st.error("""
    Database configuration not found!
    
    Please add your database credentials to Streamlit Cloud secrets:
    1. Go to your app's settings
    2. Click on 'Secrets'
    3. Add the following:
    
    [connections.mysql]
    host = "your_host"
    database = "axe_assistant"
    user = "your_user"
    password = "your_password"
    port = 3306
    """)
    st.stop()

# Updated topics list
PREDEFINED_TOPICS = [
    "forms",
    "tables",
    "images",
    "navigation",
    "color",
    "keyboard",
    "screen reader",
    "mobile",
    "pdf",
    "wcag"
]

def extract_response_time(text):
    """Extract response time from the response text"""
    if pd.isna(text):
        return None
    match = re.search(r'Time taken for first response: (\d+) seconds', text)
    if match:
        return int(match.group(1))
    return None

def extract_total_time(text):
    """Extract total time from the response text"""
    if pd.isna(text):
        return None
    match = re.search(r'Total time taken: (\d+) seconds', text)
    if match:
        return int(match.group(1))
    return None

def categorize_topic(text):
    """Categorize text into predefined topics"""
    if pd.isna(text):
        return "other"
    text = text.lower()
    for topic in PREDEFINED_TOPICS:
        if topic in text:
            return topic
    return "other"

# Database Configuration using Streamlit Secrets
def create_db_connection():
    try:
        connection = mysql.connector.connect(
            host=st.secrets["connections"]["mysql"]["host"],
            database=st.secrets["connections"]["mysql"]["database"],
            user=st.secrets["connections"]["mysql"]["user"],
            password=st.secrets["connections"]["mysql"]["password"],
            port=int(st.secrets["connections"]["mysql"]["port"])
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

@st.cache_data(ttl=600)
def load_data():
    connection = create_db_connection()
    if connection:
        try:
            query = """
                SELECT 
                    thread_id,
                    user_id,
                    client_name,
                    client_type,
                    client_sector,
                    client_country,
                    thread_created_on,
                    user_prompt,
                    response,
                    reaction,
                    feedback,
                    feedback_updated_on
                FROM axe_assistant_prompts_and_responses
            """
            
            df = pd.read_sql(query, connection)
            connection.close()
            
            # Convert timestamps
            df['thread_created_on'] = pd.to_datetime(df['thread_created_on'])
            df['feedback_updated_on'] = pd.to_datetime(df['feedback_updated_on'])
            
            # Extract response times
            df['first_response_time'] = df['response'].apply(extract_response_time)
            df['total_response_time'] = df['response'].apply(extract_total_time)
            
            # Calculate sentiment
            df['prompt_sentiment'] = df['user_prompt'].apply(lambda x: TextBlob(str(x)).sentiment.polarity if pd.notna(x) else 0)
            df['response_sentiment'] = df['response'].apply(lambda x: TextBlob(str(x)).sentiment.polarity if pd.notna(x) else 0)
            
            # Categorize topics
            df['topic'] = df['user_prompt'].apply(categorize_topic)
            
            # Add time-based features
            df['hour_of_day'] = df['thread_created_on'].dt.hour
            df['day_of_week'] = df['thread_created_on'].dt.day_name()
            df['month'] = df['thread_created_on'].dt.month_name()
            
            return df
        except Error as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def main():
    st.set_page_config(page_title="Client Interaction Analytics", layout="wide")
    st.title("Client Interaction Analysis Dashboard")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_data()
    
    if df.empty:
        st.warning("No data available from database. Please check your connection settings.")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Client filters
    st.sidebar.subheader("Client Filters")
    client_names = ["All"] + sorted(df['client_name'].dropna().unique().tolist())
    selected_client = st.sidebar.selectbox("Client Name", client_names)
    
    client_types = ["All"] + sorted(df['client_type'].dropna().unique().tolist())
    selected_type = st.sidebar.selectbox("Client Type", client_types)
    
    client_sectors = ["All"] + sorted(df['client_sector'].dropna().unique().tolist())
    selected_sector = st.sidebar.selectbox("Client Sector", client_sectors)
    
    client_countries = ["All"] + sorted(df['client_country'].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox("Client Country", client_countries)
    
    # User filter
    st.sidebar.subheader("User Filter")
    user_ids = ["All"] + sorted(df['user_id'].dropna().unique().tolist())
    selected_user = st.sidebar.selectbox("User ID", user_ids)
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    min_date = df['thread_created_on'].min().date()
    max_date = df['thread_created_on'].max().date()
    date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    
    # Apply filters
    filtered_df = df.copy()
    if selected_client != "All":
        filtered_df = filtered_df[filtered_df['client_name'] == selected_client]
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df['client_type'] == selected_type]
    if selected_sector != "All":
        filtered_df = filtered_df[filtered_df['client_sector'] == selected_sector]
    if selected_country != "All":
        filtered_df = filtered_df[filtered_df['client_country'] == selected_country]
    if selected_user != "All":
        filtered_df = filtered_df[filtered_df['user_id'] == selected_user]
    if len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['thread_created_on'].dt.date >= date_range[0]) &
            (filtered_df['thread_created_on'].dt.date <= date_range[1])
        ]
    
    # KPI Metrics
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Interactions", len(filtered_df))
    with col2:
        positive_count = filtered_df[filtered_df['reaction'] == 'thumbs-up'].shape[0]
        negative_count = filtered_df[filtered_df['reaction'] == 'thumbs-down'].shape[0]
        total_reactions = positive_count + negative_count
        positive_rate = positive_count / total_reactions if total_reactions > 0 else 0
        st.metric("Positive Reaction Rate", f"{positive_rate:.1%}")
    with col3:
        feedback_count = filtered_df['feedback'].notna().sum()
        st.metric("Feedback Responses", feedback_count)
    with col4:
        avg_response_time = filtered_df['first_response_time'].mean()
        st.metric("Average Response Time", f"{avg_response_time:.1f} seconds")
    
    # Main Visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trend Analysis", "Content Analysis", "Topic Analysis", "Response Analysis", "Client Insights"])
    
    with tab1:
        st.subheader("Interaction Trends")
        
        # Weekly interaction trends by reaction
        weekly_trends = filtered_df.groupby([pd.Grouper(key='thread_created_on', freq='W'), 'reaction']).size().reset_index()
        weekly_trends.columns = ['Date', 'Reaction', 'Count']
        fig = px.line(weekly_trends, x='Date', y='Count', color='Reaction',
                     title="Weekly Interaction Trends by Reaction")
        st.plotly_chart(fig)
        
        # Time of day analysis
        hourly_trends = filtered_df.groupby('hour_of_day').size().reset_index()
        hourly_trends.columns = ['Hour', 'Count']
        fig2 = px.bar(hourly_trends, x='Hour', y='Count',
                     title="Interaction Volume by Hour of Day")
        st.plotly_chart(fig2)
        
        # Day of week analysis
        daily_trends = filtered_df.groupby('day_of_week').size().reset_index()
        daily_trends.columns = ['Day', 'Count']
        fig3 = px.bar(daily_trends, x='Day', y='Count',
                     title="Interaction Volume by Day of Week")
        st.plotly_chart(fig3)
    
    with tab2:
        st.subheader("Content Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("Word Cloud - User Prompts")
            text = ' '.join(filtered_df['user_prompt'].dropna())
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            st.pyplot(plt)
            
            # Sentiment distribution of prompts
            fig = px.histogram(filtered_df, x='prompt_sentiment', 
                             title="Prompt Sentiment Distribution")
            st.plotly_chart(fig)
            
            # Drill down to negative sentiment
            negative_threshold = st.slider("Negative Sentiment Threshold", -1.0, 0.0, -0.2)
            negative_prompts = filtered_df[filtered_df['prompt_sentiment'] < negative_threshold]
            if not negative_prompts.empty:
                st.write(f"Negative Prompts (Sentiment < {negative_threshold})")
                st.dataframe(negative_prompts[['thread_created_on', 'user_prompt', 'prompt_sentiment']])
        
        with col2:
            st.write("Word Cloud - Responses")
            text = ' '.join(filtered_df['response'].dropna())
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            st.pyplot(plt)
            
            # Sentiment distribution of responses
            fig = px.histogram(filtered_df, x='response_sentiment', 
                             title="Response Sentiment Distribution")
            st.plotly_chart(fig)
            
            # Drill down to negative sentiment
            negative_responses = filtered_df[filtered_df['response_sentiment'] < negative_threshold]
            if not negative_responses.empty:
                st.write(f"Negative Responses (Sentiment < {negative_threshold})")
                st.dataframe(negative_responses[['thread_created_on', 'response', 'response_sentiment']])
    
    with tab3:
        st.subheader("Topic Analysis")
        
        # Topic distribution
        topic_counts = filtered_df['topic'].value_counts().reset_index()
        topic_counts.columns = ['Topic', 'Count']
        fig = px.pie(topic_counts, values='Count', names='Topic',
                    title="Topic Distribution")
        st.plotly_chart(fig)
        
        # Topic sentiment analysis
        topic_sentiment = filtered_df.groupby('topic').agg({
            'prompt_sentiment': 'mean',
            'response_sentiment': 'mean',
            'thread_id': 'count'
        }).reset_index()
        fig2 = px.scatter(topic_sentiment, x='prompt_sentiment', y='response_sentiment',
                         size='thread_id', color='topic', hover_name='topic',
                         title="Topic Sentiment Analysis")
        st.plotly_chart(fig2)
        
        # Topic reaction analysis
        topic_reaction = pd.crosstab(filtered_df['topic'], filtered_df['reaction'])
        topic_reaction = topic_reaction.reset_index()
        topic_reaction_melted = pd.melt(topic_reaction, id_vars=['topic'],
                                      var_name='Reaction', value_name='Count')
        fig3 = px.bar(topic_reaction_melted, x='topic', y='Count', color='Reaction',
                     title="Reactions by Topic")
        st.plotly_chart(fig3)
    
    with tab4:
        st.subheader("Response Analysis")
        
        # Response time distribution with better visualization
        fig = px.box(filtered_df, y='first_response_time',
                    title="Response Time Distribution (seconds)")
        fig.update_layout(yaxis_title="Response Time (seconds)")
        st.plotly_chart(fig)
        
        # Response time correlation with reactions
        st.subheader("Response Time vs Reaction Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Box plot of response time by reaction
            fig_reaction = px.box(filtered_df, x='reaction', y='first_response_time',
                                title="Response Time Distribution by Reaction")
            fig_reaction.update_layout(xaxis_title="Reaction", yaxis_title="Response Time (seconds)")
            st.plotly_chart(fig_reaction)
            
            # Calculate and display correlation metrics
            reaction_stats = filtered_df.groupby('reaction').agg({
                'first_response_time': ['mean', 'median', 'count']
            }).reset_index()
            reaction_stats.columns = ['Reaction', 'Mean Time', 'Median Time', 'Count']
            st.write("Response Time Statistics by Reaction:")
            st.dataframe(reaction_stats)
        
        with col2:
            # Scatter plot of response time vs sentiment with reaction coloring
            fig_scatter = px.scatter(filtered_df, x='first_response_time', y='prompt_sentiment',
                                   color='reaction', title="Response Time vs Sentiment by Reaction")
            fig_scatter.update_layout(xaxis_title="Response Time (seconds)", yaxis_title="Prompt Sentiment")
            st.plotly_chart(fig_scatter)
            
            # Calculate success rate by response time ranges
            time_ranges = pd.cut(filtered_df['first_response_time'], 
                               bins=[0, 5, 10, 15, 20, float('inf')],
                               labels=['0-5s', '5-10s', '10-15s', '15-20s', '20s+'])
            success_rate = filtered_df.groupby(time_ranges)['reaction'].apply(
                lambda x: (x == 'thumbs-up').mean()
            ).reset_index()
            success_rate.columns = ['Response Time Range', 'Success Rate']
            st.write("Success Rate by Response Time Range:")
            st.dataframe(success_rate)
        
        # Response time by hour of day
        fig2 = px.box(filtered_df, x='hour_of_day', y='first_response_time',
                     title="Response Time by Hour of Day")
        fig2.update_layout(xaxis_title="Hour of Day", yaxis_title="Response Time (seconds)")
        st.plotly_chart(fig2)
        
        # Response time by topic
        fig3 = px.box(filtered_df, x='topic', y='first_response_time',
                     title="Response Time by Topic")
        fig3.update_layout(xaxis_title="Topic", yaxis_title="Response Time (seconds)")
        st.plotly_chart(fig3)
        
        # Drill down to specific time ranges
        st.subheader("Drill Down Analysis")
        time_threshold = st.slider("Response Time Threshold (seconds)", 0, 60, 10)
        slow_responses = filtered_df[filtered_df['first_response_time'] > time_threshold]
        if not slow_responses.empty:
            st.write(f"Responses Taking More Than {time_threshold} Seconds")
            st.dataframe(slow_responses[['thread_created_on', 'user_prompt', 'first_response_time', 'reaction']])
    
    with tab5:
        st.subheader("Client Insights")
        
        # Client distribution
        client_dist = filtered_df['client_name'].value_counts().head(10).reset_index()
        client_dist.columns = ['Client', 'Count']
        fig = px.bar(client_dist, x='Client', y='Count',
                    title="Top 10 Clients by Interaction Volume")
        st.plotly_chart(fig)
        
        # Client type analysis
        client_type_dist = filtered_df.groupby('client_type').agg({
            'thread_id': 'count',
            'first_response_time': 'mean',
            'prompt_sentiment': 'mean',
            'response_sentiment': 'mean'
        }).reset_index()
        
        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.pie(client_type_dist, values='thread_id', names='client_type',
                         title="Distribution by Client Type")
            st.plotly_chart(fig2)
        
        with col2:
            fig3 = px.bar(client_type_dist, x='client_type', y='first_response_time',
                         title="Average Response Time by Client Type")
            st.plotly_chart(fig3)
        
        # Client sector analysis
        sector_analysis = filtered_df.groupby('client_sector').agg({
            'thread_id': 'count',
            'first_response_time': 'mean',
            'prompt_sentiment': 'mean',
            'response_sentiment': 'mean'
        }).reset_index()
        
        fig4 = px.scatter(sector_analysis, x='prompt_sentiment', y='response_sentiment',
                         size='thread_id', color='client_sector', hover_name='client_sector',
                         title="Client Sector Performance Analysis")
        st.plotly_chart(fig4)
        
        # Country analysis
        country_analysis = filtered_df.groupby('client_country').agg({
            'thread_id': 'count',
            'first_response_time': 'mean',
            'prompt_sentiment': 'mean',
            'response_sentiment': 'mean'
        }).reset_index()
        
        fig5 = px.choropleth(country_analysis, locations='client_country',
                            locationmode='country names',
                            color='thread_id',
                            title="Global Distribution of Interactions")
        st.plotly_chart(fig5)

if __name__ == "__main__":
    main() 