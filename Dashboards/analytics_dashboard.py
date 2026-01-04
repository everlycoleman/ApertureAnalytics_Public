import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

DASH_NAME = "Analytics Dashboard"
DASH_DESCRIPTION = "Real-time website analytics from PostgreSQL database with visitor metrics and trends."

def init_dashboard(server, get_analytics_data):
    """Initializes the Analytics Dashboard using real database data"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/analytics/',
        external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME]
    )

    # Initial layout (essential to avoid NoLayoutException)
    dash_app.layout = dbc.Container([
        # Navigation header
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-arrow-left me-2"),
                        "Back to Dashboards"
                    ], href="/dashboards", color="outline-primary", external_link=True),
                    dbc.Button([
                        html.I(className="fas fa-home me-2"),
                        "Home"
                    ], href="/", color="outline-secondary", external_link=True),
                ])
            ], width=12, className="mb-4")
        ]),

        dbc.Row([
            dbc.Col(html.H1("Analytics Dashboard", className="text-center mb-4"), width=12)
        ]),

        # Refresh button
        dbc.Row([
            dbc.Col([
                dbc.Button("Refresh Data", id="refresh-btn", n_clicks=0, color="success", className="mb-4")
            ], className="text-center")
        ]),

        # Charts container
        dbc.Row([
            dbc.Col(id="analytics-content", width=12, children=[
                dbc.Alert("Loading analytics data...", color="info")
            ])
        ]),

    ], fluid=True, className="py-4")

    @dash_app.callback(
        Output('analytics-content', 'children'),
        [Input('refresh-btn', 'n_clicks')]
    )
    def update_analytics_dashboard(n_clicks):
        try:
            # Get data from database using the passed function
            analytics_data = get_analytics_data()

            if not analytics_data:
                return dbc.Alert("No analytics data available. Please check your database connection.",
                                 color="warning", className="mt-3")

            # Convert to DataFrame
            df = pd.DataFrame(analytics_data)
            df['date'] = pd.to_datetime(df['date'])
        except Exception as e:
            return dbc.Alert(f"Error loading analytics data: {e}", color="danger", className="mt-3")

        # Create visualizations
        visitors_fig = px.line(df, x='date', y='visitors',
                               title="Daily Visitors Over Time",
                               labels={'visitors': 'Number of Visitors', 'date': 'Date'},
                               template='plotly_dark')

        pageviews_fig = px.area(df, x='date', y='page_views',
                                title="Daily Page Views",
                                labels={'page_views': 'Page Views', 'date': 'Date'},
                                template='plotly_dark')

        bounce_rate_fig = px.line(df, x='date', y='bounce_rate',
                                  title="Bounce Rate Trend",
                                  labels={'bounce_rate': 'Bounce Rate', 'date': 'Date'},
                                  template='plotly_dark')

        session_duration_fig = px.bar(df, x='date', y='avg_session_duration',
                                      title="Average Session Duration",
                                      labels={'avg_session_duration': 'Duration (seconds)', 'date': 'Date'},
                                      template='plotly_dark')

        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Website Visitors", className="mb-0")),
                        dbc.CardBody(dcc.Graph(figure=visitors_fig))
                    ], className="mb-4")
                ], md=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Page Views", className="mb-0")),
                        dbc.CardBody(dcc.Graph(figure=pageviews_fig))
                    ], className="mb-4")
                ], md=6)
            ]),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Bounce Rate", className="mb-0")),
                        dbc.CardBody(dcc.Graph(figure=bounce_rate_fig))
                    ], className="mb-4")
                ], md=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Session Duration", className="mb-0")),
                        dbc.CardBody(dcc.Graph(figure=session_duration_fig))
                    ], className="mb-4")
                ], md=6)
            ]),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Summary Statistics", className="mb-0")),
                        dbc.CardBody([
                            html.P(f"Average Daily Visitors: {df['visitors'].mean():.1f}"),
                            html.P(f"Average Page Views: {df['page_views'].mean():.1f}"),
                            html.P(f"Average Bounce Rate: {df['bounce_rate'].mean():.2%}"),
                            html.P(f"Total Period: {len(df)} days"),
                            html.P(f"Total Unique Visitors: {df['unique_visitors'].sum():,}")
                        ])
                    ], className="mb-4")
                ], md=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Recent Performance", className="mb-0")),
                        dbc.CardBody([
                            html.P(f"Yesterday's Visitors: {df.iloc[0]['visitors'] if len(df) > 0 else 'N/A'}"),
                            html.P(f"Best Day Visitors: {df['visitors'].max()}"),
                            html.P(f"Best Day Page Views: {df['page_views'].max()}"),
                            html.P(f"Lowest Bounce Rate: {df['bounce_rate'].min():.2%}")
                        ])
                    ], className="mb-4")
                ], md=6)
            ])
        ])

    return dash_app
