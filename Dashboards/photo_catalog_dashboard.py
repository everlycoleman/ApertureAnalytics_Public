import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DASH_NAME = "Photo Metadata Analysis"
DASH_DESCRIPTION = "Interactive data visualization of my Lightroom Catalog."

def init_dashboard(server, photo_catalog_service):
    """Initializes the Photo Metadata Analysis Dashboard"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/photos/',
        external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME],
        external_scripts=[
            "https://cdn.jsdelivr.net/npm/d3@7",
            "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6"
        ]
    )

    # Initial layout
    dash_app.layout = dbc.Container([
        dcc.Store(id='heatmap-data-store'),
        dcc.Store(id='catalog-data-store'),
        dcc.Interval(
            id='interval-component',
            interval=12 * 60 * 60 * 1000, # in milliseconds (12 hours)
            n_intervals=0
        ),
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
            dbc.Col([
                html.H1("Photo Metadata Analysis", className="text-center mb-2"),
                html.P("Allow Several Seconds to Load. Best Viewed in Landscape Mode.",
                       className="text-center text-muted mb-4")
            ], width=12)
        ]),

        html.Div(id='dashboard-content'),
        html.Div(id='dummy-output-heatmap', style={'display': 'none'}),
    ], fluid=True, className="py-4")

    @dash_app.callback(
        [Output('dashboard-content', 'children'),
         Output('heatmap-data-store', 'data'),
         Output('catalog-data-store', 'data')],
        [Input('interval-component', 'n_intervals')]
    )
    def update_dashboard_content(n_intervals):
        # Get data from service with optimized methods
        try:
            summary = photo_catalog_service.get_catalog_summary_stats()
            camera_dist = photo_catalog_service.get_camera_distribution()
            lens_usage = photo_catalog_service.get_lens_usage()
            heatmap_data = photo_catalog_service.get_heatmap_data()
            interactive_data = photo_catalog_service.get_interactive_plot_data()
            
            if not summary or summary['total_photos'] == 0:
                return dbc.Alert("No data available. Please check your database connection.", color="warning"), [], []
            
            logger.info(f"Loaded {summary['total_photos']} records for photo catalog dashboard")
        except Exception as e:
            logger.error(f"Error fetching catalog data: {e}", exc_info=True)
            return dbc.Alert(f"Error loading data: {e}", color="danger"), [], []

        # Convert to DataFrames for easier plotting (still smaller than full dataset)
        df_camera = pd.DataFrame(camera_dist)
        df_lens = pd.DataFrame(lens_usage)
        
        # Determine camera models for dropdown
        unique_cameras = sorted(df_camera['CameraModel'].unique()) if not df_camera.empty else []

        content = [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Total Images", className="mb-0")),
                        dbc.CardBody([
                            html.H1(f"{summary['total_photos']:,}", className="text-info text-center"),
                            html.P("Images in Catalog", className="text-light text-center")
                        ])
                    ], className="shadow-sm")
                ], width=4),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Cumulative Exposure Time", className="mb-0")),
                        dbc.CardBody([
                            html.H1(f"{summary['total_exposure_time'] or 0:.2f}", className="text-info text-center"),
                            html.P(" Time in Seconds", className="text-light text-center")
                        ])
                    ], className="shadow-sm")
                ], width=4),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Catalog Size", className="mb-0")),
                        dbc.CardBody([
                            html.H1(f"{summary['total_size_gb'] or 0:.2f}", className="text-info text-center"),
                            html.P("Catalog Size in GB", className="text-light text-center")
                        ])
                    ], className="shadow-sm")
                ], width=4)
            ], className="g-4"),

            html.Hr(),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Camera Models", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(
                                id='camera-model-plot',
                                figure=px.pie(df_camera, names='CameraModel', values='count', title="Distribution of Camera Models", template='plotly_dark')
                                if not df_camera.empty else {}
                            )
                        ])
                    ], className="mb-4")
                ], md=6),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Lens Models", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(
                                id='lens-model-plot',
                                figure=px.bar(
                                    df_lens,
                                    x='Count',
                                    y='LensModel',
                                    color='CameraModel',
                                    orientation='h',
                                    title="Lens Model Usage by Camera (>10 records)",
                                    labels={'Count': 'Count', 'LensModel': 'Lens Model', 'CameraModel': 'Camera Model'},
                                    template='plotly_dark'
                                ).update_layout(
                                    barmode='stack',
                                    yaxis={'categoryorder': 'total ascending'}
                                ) if not df_lens.empty else {}
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
                            html.Label("Select Camera Model:", className="fw-bold mb-2"),
                            dcc.Dropdown(
                                id='camera-dropdown',
                                options=[{'label': cam, 'value': cam} for cam in unique_cameras],
                                value=(unique_cameras[0] if unique_cameras else None),
                                multi=True,
                                className="mb-3"
                            ),
                            dbc.Row([
                                dbc.Col(dcc.Graph(id='focal-length-plot'), md=4),
                                dbc.Col(dcc.Graph(id='iso-plot'), md=4),
                                dbc.Col(dcc.Graph(id='shutter-plot'), md=4),
                            ])
                        ])
                    ])
                ], width=12)
            ]),

            html.Hr(),

            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H3("Photo Activity Heatmap", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id='activity-heatmap-container', style={'overflowX': 'auto'})
                        ])
                    ], className="mb-4")
                ], width=12)
            ]),
        ]
        
        return content, heatmap_data, interactive_data

    dash_app.clientside_callback(
        """
        function(data) {
            if (!data || data.length === 0) return "";
            
            // Give Dash a moment to render the container
            setTimeout(() => {
                const container = document.getElementById('activity-heatmap-container');
                if (!container) return;
                
                container.innerHTML = '';
                
                // Parse date strings to JS Dates
                const parsedData = data.map(d => ({
                    date: d3.utcParse("%Y-%m-%d")(d.date),
                    count: d.count
                }));

                const start = d3.utcYear(d3.min(parsedData, d => d.date));
                const end = d3.utcDay.offset(d3.max(parsedData, d => d.date));
                
                // Helper to map dates to calendar grid
                const calendar = ({date = d => d, ...options} = {}) => ({
                    x: d => d3.utcWeek.count(d3.utcYear(date(d)), date(d)),
                    y: d => date(d).getUTCDay(),
                    fy: d => date(d).getUTCFullYear(),
                    ...options
                });

                const plot = Plot.plot({
                    width: Math.max(container.clientWidth, 950),
                    height: (d3.utcYear.count(start, end) + 1) * 160,
                    axis: null,
                    padding: 0,
                    marginLeft: 80,
                    style: {
                        backgroundColor: "transparent",
                        color: "#fff",
                        fontFamily: "inherit"
                    },
                    x: {
                        domain: d3.range(54),
                        padding: 0
                    },
                    y: {
                        axis: "left",
                        domain: [-1, 0, 1, 2, 3, 4, 5, 6],
                        tickFormat: Plot.formatWeekday("en", "narrow"),
                        tickSize: 0
                    },
                    fy: {
                        padding: 0.1,
                        reverse: true
                    },
                    color: {
                        scheme: "viridis",
                        legend: true,
                        label: "Photos Taken",
                        zero: true
                    },
                    marks: [
                        // Year labels on the left
                        Plot.text(
                            d3.utcYears(start, end),
                            calendar({
                                text: d3.utcFormat("%Y"),
                                frameAnchor: "right",
                                x: 0,
                                y: 3, // Vertically centered in the 7 rows
                                dx: -65,
                                fontSize: 16,
                                fontWeight: "bold"
                            })
                        ),
                        // Month labels on top
                        Plot.text(
                            d3.utcMonths(start, end),
                            calendar({
                                text: d3.utcFormat("%b"),
                                frameAnchor: "left",
                                y: -1
                            })
                        ),
                        // Empty cells for all days to show the grid
                        Plot.cell(d3.utcDays(start, end), calendar({
                            fill: "#fff",
                            fillOpacity: 0.05,
                            inset: 0.5
                        })),
                        // Data cells
                        Plot.cell(parsedData, calendar({
                            date: d => d.date,
                            fill: "count",
                            inset: 0.5,
                            title: d => `${d3.utcFormat("%Y-%m-%d")(d.date)}: ${d.count} photos`
                        })),
                        // Day numbers
                        Plot.text(d3.utcDays(start, end), calendar({
                            text: d3.utcFormat("%-d"),
                            fontSize: 8,
                            fill: "#fff",
                            fillOpacity: 0.5,
                            pointerEvents: "none"
                        }))
                    ]
                });
                
                container.appendChild(plot);
            }, 200);
            
            return "";
        }
        """,
        Output('dummy-output-heatmap', 'children'),
        [Input('heatmap-data-store', 'data')]
    )

    @dash_app.callback(
        [Output('focal-length-plot', 'figure'),
         Output('iso-plot', 'figure'),
         Output('shutter-plot', 'figure')],
        [Input('camera-dropdown', 'value'),
         Input('catalog-data-store', 'data')]
    )
    def update_interactive_plots(selected_cameras, stored_data):
        if not stored_data:
            return {}, {}, {}

        df = pd.DataFrame(stored_data)
        if df.empty:
            return {}, {}, {}

        if not selected_cameras:
            filtered_df = df.copy()
        else:
            if isinstance(selected_cameras, str):
                selected_cameras = [selected_cameras]
            filtered_df = df[df['CameraModel'].isin(selected_cameras)].copy()

        # 1. Focal Length Plot
        focal_df = filtered_df.copy()
        focal_df['FocalLength'] = pd.to_numeric(focal_df['FocalLength'], errors='coerce')
        focal_df = focal_df.dropna(subset=['FocalLength'])
        focal_fig = px.histogram(focal_df, x='FocalLength',
                                title="Focal Length Distribution",
                                template='plotly_dark')
        focal_fig.update_xaxes(categoryorder='category ascending')

        # 2. ISO Plot
        iso_df = filtered_df.copy()
        iso_df['ISO'] = pd.to_numeric(iso_df['ISO'], errors='coerce')
        iso_df = iso_df.dropna(subset=['ISO'])
        # Sort ISO values numerically for better histogram presentation
        iso_df = iso_df.sort_values('ISO')
        iso_fig = px.histogram(iso_df, x='ISO',
                              title="ISO Distribution",
                              template='plotly_dark')
        iso_fig.update_xaxes(type='category') # Keep standard ISO stops as categories

        # 3. Shutter Speed Plot
        shutter_df = filtered_df.copy()
        shutter_df = shutter_df[(shutter_df['shutter'].notna()) & (shutter_df['shutter'] != '')]
        
        # To sort shutter speeds, we need their numeric value
        def shutter_to_numeric(s):
            try:
                if '/' in str(s):
                    num, den = s.split('/')
                    return float(num) / float(den)
                return float(s)
            except:
                return 0

        shutter_df['shutter_val'] = shutter_df['shutter'].apply(shutter_to_numeric)
        shutter_df = shutter_df.sort_values('shutter_val')
        
        shutter_fig = px.histogram(shutter_df, x='shutter',
                                  title="Shutter Speed Distribution",
                                  template='plotly_dark')
        # Ensure x-axis follows the numeric sort order of the shutter speeds
        shutter_fig.update_xaxes(categoryorder='array', categoryarray=shutter_df['shutter'].unique())

        return focal_fig, iso_fig, shutter_fig

    return dash_app
