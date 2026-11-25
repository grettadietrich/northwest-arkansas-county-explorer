# Northwest Arkansas County Explorer

Explore six demographic measures across Benton, Washington, Madison, and Carroll counties.
Choose a measure and filter counties in the sidebar. Hover over the map and bars for exact
display values. Click a table header to sort all six estimates by that column.

## Run on Windows

Open PowerShell and paste these commands one at a time. They open the project folder,
create an isolated Python environment, install the dependencies, and start Streamlit.

```powershell
Set-Location "$env:USERPROFILE\OneDrive\Desktop\Project"
& "$env:LOCALAPPDATA\Python\bin\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If your Python is available as `py`, you can use `py -m venv .venv` in the second line.
Open the Local URL printed by Streamlit, usually http://localhost:8501. Press **Ctrl+C**
in PowerShell to stop the app. On subsequent launches, run only the first and last commands.

## Census data and cache

- Demographics use the [2020–2024 ACS 5-year Detailed Tables](https://www.census.gov/programs-surveys/acs/data/summary-file.html).
  Population is B01003, household income is B19013, median age is B01002, education is
  B15003 (lines 22–25 divided by line 1), poverty is B17001 (line 2 divided by line 1),
  and median owner-occupied home value is B25077.
- The map uses the [2024 Census cartographic county boundaries](https://www.census.gov/geographies/mapping-files/2024/geo/carto-boundary-file.html),
  joined to the estimates by five-digit county FIPS codes.
- The first launch needs internet access. The app downloads public files without a subscription
  or API key and saves the four counties' estimates and boundaries to `.census-cache/`.
  Later launches reuse those files offline. To fetch the same reporting period again, stop the
  app and remove `.census-cache/acs-2024-counties.json`.
- Missing estimates stay empty and appear gray on the map. The dashboard shows five-year
  survey estimates and displays point estimates without margins of error.
