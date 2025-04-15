# Axe Assistant Analytics Dashboard

A comprehensive analytics dashboard for monitoring and analyzing interactions with the Axe Assistant. This dashboard provides insights into user interactions, response times, sentiment analysis, and topic categorization.

## Features

- **Real-time Analytics**: Monitor user interactions and response metrics
- **Sentiment Analysis**: Analyze user prompts and responses using TextBlob
- **Topic Categorization**: Automatically categorize interactions into predefined topics
- **Response Time Analysis**: Track and visualize response times
- **Interactive Visualizations**: Dynamic charts and graphs using Plotly
- **Word Clouds**: Visual representation of common terms in prompts and responses
- **Client Insights**: Detailed analysis of client interactions and feedback

## Prerequisites

- Python 3.8 or higher
- MySQL Server (local installation)
- Required Python packages (listed in requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/BhavayChopra/Axe_Dashboard.git
cd Axe_Dashboard
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Set up your database credentials:
   - Create a new file named `.env` in the project root directory
   - Copy the contents from `.env.example` to your `.env` file
   - Update the following values in your `.env` file:
     ```
     DB_HOST=localhost
     DB_NAME=axe_assistant
     DB_USER=your_mysql_username
     DB_PASSWORD=your_mysql_password
     DB_PORT=3306
     ```
   - Replace `your_mysql_username` and `your_mysql_password` with your actual MySQL credentials
   - Make sure your MySQL server is running locally on port 3306

## Usage

1. Start the Streamlit app:
```bash
streamlit run axe_analysis_improved.py
```

2. Access the dashboard in your web browser at `http://localhost:8501`

## Dashboard Sections

1. **Key Metrics**: Overview of total interactions, positive reaction rate, feedback responses, and average response time
2. **Trend Analysis**: Weekly interaction trends and time-based analysis
3. **Content Analysis**: Word clouds and sentiment analysis of prompts and responses
4. **Topic Analysis**: Distribution and sentiment analysis by topic
5. **Response Analysis**: Detailed analysis of response times and their impact
6. **Client Insights**: Analysis of client interactions and feedback

## Database Configuration

The dashboard expects a MySQL database with the following structure:
- Table: `axe_assistant_prompts_and_responses`
- Required fields: thread_id, user_id, client_name, client_type, client_sector, client_country, thread_created_on, user_prompt, response, reaction, feedback, feedback_updated_on

If you need to create the database and table, you can use the following SQL commands:
```sql
CREATE DATABASE axe_assistant;
USE axe_assistant;

CREATE TABLE axe_assistant_prompts_and_responses (
    thread_id VARCHAR(255),
    user_id VARCHAR(255),
    client_name VARCHAR(255),
    client_type VARCHAR(255),
    client_sector VARCHAR(255),
    client_country VARCHAR(255),
    thread_created_on DATETIME,
    user_prompt TEXT,
    response TEXT,
    reaction VARCHAR(255),
    feedback TEXT,
    feedback_updated_on DATETIME
);
```

## Troubleshooting

If you encounter connection issues:
1. Verify your MySQL server is running: `mysql.server status`
2. Check your credentials in the `.env` file
3. Ensure the database and table exist with the correct structure
4. Verify your MySQL user has the necessary permissions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any questions or support, please contact the repository owner. 