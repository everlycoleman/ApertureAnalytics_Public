import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc

DASH_NAME = "Data Visualization"
DASH_DESCRIPTION = "Interactive data visualization dashboard with scatter plots and histograms using Dash and Bootstrap."

def init_dashboard(server):
    """Initializes the Sample Data Visualization Dashboard"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/data/',
        external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME]
    )

    # Sample data
    df = pd.DataFrame({
        'x': np.random.randn(100),
        'y': np.random.randn(100),
        'category': np.random.choice(['A', 'B', 'C'], 100)
    })

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
            dbc.Col(html.H1("Data Visualization Dashboard", className="text-center mb-4"), width=12)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H3("Box Plot", className="mb-0")),

                ])
            ])
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H3("Scatter Plot", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id='scatter-plot',
                            figure=px.scatter(df, x='x', y='y', color='category',
                                              title="Random Data Scatter Plot",
                                              template='plotly_dark')
                        )
                    ])
                ], className="mb-4")
            ], md=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H3("Histogram", className="mb-0")),
                    dbc.CardBody([
                        dcc.Graph(
                            id='histogram',
                            figure=px.histogram(df, x='x', color='category',
                                                title="Distribution of X Values",
                                                template='plotly_dark')
                        )
                    ])
                ], className="mb-4")
            ], md=6)
        ]),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H3("Interactive Controls", className="mb-0")),
                    dbc.CardBody([
                        html.Label("Select Category:", className="fw-bold mb-2"),
                        dcc.Dropdown(
                            id='category-dropdown',
                            options=[{'label': cat, 'value': cat} for cat in df['category'].unique()],
                            value=df['category'].unique()[0],
                            multi=True,
                            className="mb-3"
                        ),
                        dcc.Graph(id='filtered-plot')
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True, className="py-4")

    @dash_app.callback(
        Output('filtered-plot', 'figure'),
        [Input('category-dropdown', 'value')]
    )
    def update_filtered_plot(selected_categories):
        if not selected_categories:
            selected_categories = df['category'].unique()
        if isinstance(selected_categories, str):
            selected_categories = [selected_categories]

        filtered_df = df[df['category'].isin(selected_categories)]
        fig = px.box(filtered_df, x='category', y='y',
                     title="Box Plot by Category",
                     template='plotly_dark')
        return fig

    return dash_app
