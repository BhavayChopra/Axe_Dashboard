# Axe Assistant Analytics Dashboard

A comprehensive analytics dashboard for analyzing Axe Assistant interactions, built with Streamlit.

## Features

- Real-time data visualization
- Topic analysis and classification
- Sentiment analysis of prompts and responses
- Response time analysis
- Client insights and trends
- Interactive filtering and drill-down capabilities

## Deployment

This dashboard is deployed on Streamlit Community Cloud. To access it:

1. Visit the dashboard at: [Your Streamlit Cloud URL]
2. No installation or setup required
3. Access is restricted to authorized users

## Local Development

If you want to run the dashboard locally:

1. Clone the repository:
```bash
git clone https://github.com/yourusername/axe-assistant-analytics.git
cd axe-assistant-analytics
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the dashboard:
```bash
streamlit run axe_analysis_improved.py
```

## Dashboard Sections

1. **Trend Analysis**
   - Weekly interaction trends
   - Hourly usage patterns
   - Daily activity analysis

2. **Content Analysis**
   - Word clouds for prompts and responses
   - Sentiment distribution
   - Negative sentiment drill-down

3. **Topic Analysis**
   - Topic distribution
   - Sentiment by topic
   - Reaction analysis by topic

4. **Response Analysis**
   - Response time distribution
   - Response time vs reaction analysis
   - Time-based performance metrics

5. **Client Insights**
   - Client distribution
   - Sector analysis
   - Global interaction patterns

## Security

- The dashboard is deployed on Streamlit Community Cloud
- Database credentials are securely stored in Streamlit's secrets management
- Access is restricted to authorized users

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please contact the maintainers directly. 