# Aperture Analytics

Aperture Analytics is a comprehensive Flask-based web application designed for photographers and data enthusiasts. It combines a high-performance photography gallery, interactive data dashboards for Lightroom catalog analysis, and a markdown-powered technical blog.

## 🌟 Features

### 📸 Photography Gallery
- **Cloudinary Integration**: High-performance image hosting and dynamic transformations.
- **Infinite Scroll**: Seamless browsing experience with lazy loading.
- **Rich Metadata**: Automatically extracts and displays EXIF (Camera, Lens, Exposure), IPTC (Keywords, Location), and XMP data.
- **Smart Collections**: Filter by category, location, or search term; view most-viewed or random selections.

### 📊 Data Dashboards
- **Lightroom Catalog Analysis**: Visualizes data from large catalogs (60,000+ records).
- **Interactive Visualizations**: Built with Plotly Dash, featuring:
    - **Camera & Lens Distribution**: Pie and bar charts showing gear usage.
    - **Exposure Analysis**: Histograms for Focal Length, ISO, and Shutter Speed.
    - **Activity Heatmap**: A D3.js-powered calendar view of photographic activity over time.
- **Optimized Performance**: Leverages database-level aggregation for fast loading of large datasets.

### ✍️ Technical Blog
- **Markdown-Powered**: Articles are written in Markdown with YAML frontmatter.
- **Auto-Sync**: Utility scripts synchronize local markdown files with the PostgreSQL database.
- **Feature-Rich**: Supports syntax highlighting, tables, and image integration.

### ⚙️ Metadata & Management Engine
- **Automated Uploads**: Streamlined workflow for uploading new photos and extracting metadata.
- **Multi-Source Extraction**: Robust processing of EXIF, IPTC, and XMP data.
- **Database Migrations**: Automatic schema management for the gallery and blog systems.

## 🛠️ Tech Stack

- **Backend**: Python 3.x, [Flask](https://flask.palletsprojects.com/)
- **Dashboards**: [Plotly Dash](https://dash.plotly.com/), Pandas, NumPy
- **Database**: PostgreSQL with [SQLAlchemy](https://www.sqlalchemy.org/) and [Psycopg2](https://www.psycopg.org/)
- **Frontend**: Bootstrap 5, [Bootswatch](https://bootswatch.com/), Font Awesome
- **Image Hosting**: [Cloudinary](https://cloudinary.com/)
- **Deployment**: Gunicorn, Procfile-ready

## 📂 Project Structure

```text
├── Dashboards/           # Plotly Dash application definitions
├── posts/                # Markdown source files for blog articles
├── Routes/               # Modular Flask Blueprints (API, Admin, Main)
├── Scripts/              # Utility scripts for data sync and maintenance
│   ├── PhotoUpload.py    # Handles Cloudinary uploads & metadata extraction
│   ├── sync_blog_posts.py# Syncs markdown files to the database
│   └── CleanupPhotos.py  # Synchronizes local storage with DB/Cloudinary
├── Services/             # Business logic and database access layers
├── static/               # CSS, JS, and local assets
├── templates/            # Jinja2 HTML templates
├── app.py                # Main application entry point
├── database.py           # Database connection and table definitions
├── requirements.txt      # Project dependencies
└── config/               # Configuration files (.env, config.toml)
```

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL Database
- Cloudinary Account

### Configuration
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Flasksite
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   Create a `.env` file in the `config/` directory with the following variables:
   ```env
   DB_External_URL=postgresql://user:password@host:port/dbname
   URL_CLOUDINARY=cloudinary://api_key:api_secret@cloud_name
   API_KEY_CLOUDINARY=your_api_key
   API_SECRET_CLOUDINARY=your_api_secret
   ```

4. **Initialize Database**:
   The application will automatically create the necessary tables on the first run.

5. **Run the Application**:
   ```bash
   python app.py
   ```
   The site will be available at `http://localhost:5000`.

## 🛠️ Maintenance & Utility Scripts

- **Upload Photos**: Place images in `Photo_Uploads/New` and run `python Scripts/PhotoUpload.py`.
- **Sync Blog**: Update or add markdown files in `posts/` and run `python Scripts/sync_blog_posts.py`.
- **Cleanup**: To remove orphaned database records or Cloudinary assets, run `python Scripts/CleanupPhotos.py`.
- **Metadata Refresh**: To re-process all photo metadata, run `python Scripts/createmetadatatable.py --refresh`.

## 📝 License
[Specify License, e.g., MIT]
