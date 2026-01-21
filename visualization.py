import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def reverse_heb(s):
    """
    Reverses Hebrew strings for proper display in Matplotlib.
    Handles parenthesis replacement to avoid mirroring issues.
    """
    if s is None:
        return ""
    s = str(s).replace('(', 'TEMP').replace(')', '(').replace('TEMP', ')')
    return s[::-1]


# --- Database Connection ---
db_path = "/home/amitaloni890/FlyTAU/flytau.db"
con = sqlite3.connect(db_path)

# --- Query 1: Revenue breakdown ---
query_revenue = """
SELECT 
    a.Size AS Airplane_Size, 
    a.Manufacturer AS Airplane_Manufacturer, 
    a.Class_Type AS Cabin_Class,
    ROUND(SUM(o.Total_Price), 2) AS Total_Revenue
FROM Orders o
JOIN Flights f ON o.Flight_IDFK = f.Flight_ID
JOIN Airplanes a ON f.Airplane_IDFK = a.Airplane_ID AND f.Class_TypeFK = a.Class_Type
WHERE EXISTS (
    SELECT 1 FROM Tickets t 
    WHERE t.Order_IDFK = o.Order_ID 
    AND t.Flight_IDFK = f.Flight_ID
    AND (
        (a.Class_Type = 'Business' AND t.Row_Num <= a.Number_of_rows)
        OR 
        (a.Class_Type = 'Economy' AND t.Row_Num > 
            COALESCE((SELECT a2.Number_of_rows FROM Airplanes a2 
                      WHERE a2.Airplane_ID = a.Airplane_ID AND a2.Class_Type = 'Business'), 0))
    )
)
GROUP BY a.Size, a.Manufacturer, a.Class_Type
ORDER BY Total_Revenue DESC;
"""

# --- Query 2: Crew Flight Hours ---
query_crew = """
SELECT 
    fc.Employee_ID,
    fc.First_Name,
    fc.Last_Name,
    fc.Role, 
    SUM(CASE WHEN r.Duration/60.0 <= 6 AND f.Status = 'Completed' THEN ROUND(r.Duration/60.0,1) ELSE 0 END) AS Short_Flight_Hours,
    SUM(CASE WHEN r.Duration/60.0 > 6 AND f.Status = 'Completed' THEN ROUND(r.Duration/60.0,1) ELSE 0 END) AS Long_Flight_Hours
FROM FlightCrew fc
LEFT JOIN Flight_assigned fa ON fc.Employee_ID = fa.Employee_IDFK
LEFT JOIN (
    SELECT DISTINCT Flight_ID, Origin_AirportFK, Destination_AirportFK, Status 
    FROM Flights
) f ON fa.Flight_IDFK = f.Flight_ID
LEFT JOIN Routes r ON f.Origin_AirportFK = r.Origin_Airport 
                 AND f.Destination_AirportFK = r.Destination_Airport
GROUP BY fc.Employee_ID, fc.First_Name, fc.Last_Name, fc.Role;
"""

df_rev = pd.read_sql(query_revenue, con)
df_crew = pd.read_sql(query_crew, con)
con.close()

# --- Visualization 1: Revenue Report ---
if not df_rev.empty:
    manufacturers = sorted(df_rev['Airplane_Manufacturer'].unique())
    x = np.arange(len(manufacturers))
    width = 0.35
    fig1, ax1 = plt.subplots(figsize=(12, 7))

    color_small_econ = '#DCD0FF'  # Lavender for small planes
    color_white = '#FFFFFF'
    hatch_biz = '///'

    for i, m in enumerate(manufacturers):
        m_data = df_rev[df_rev['Airplane_Manufacturer'] == m]

        # 1. Business Bar (Left column)
        biz_total = m_data[m_data['Cabin_Class'] == 'Business']['Total_Revenue'].sum()
        ax1.bar(x[i] - width / 2, biz_total, width, color=color_white, hatch=hatch_biz,
                edgecolor='black', linewidth=1.2)
        if biz_total > 0:
            ax1.text(x[i] - width / 2, biz_total + 100, f'${biz_total:,.0f}',
                     ha='center', va='bottom', fontsize=9, fontweight='bold')

        # 2. Economy Stacked Bar (Right column - Large & Small)
        econ_large = m_data[(m_data['Cabin_Class'] == 'Economy') & (m_data['Airplane_Size'] == 'large')][
            'Total_Revenue'].sum()
        econ_small = m_data[(m_data['Cabin_Class'] == 'Economy') & (m_data['Airplane_Size'] == 'small')][
            'Total_Revenue'].sum()

        ax1.bar(x[i] + width / 2, econ_large, width, color=color_white, edgecolor='black', linewidth=1.2)
        ax1.bar(x[i] + width / 2, econ_small, width, bottom=econ_large, color=color_small_econ, edgecolor='black',
                linewidth=1.2)

        # Labels INSIDE Economy segments
        # Label for Bottom part - White
        if econ_large > 100:
            ax1.text(x[i] + width / 2, econ_large / 2, f'${econ_large:,.0f}',
                     ha='center', va='center', fontsize=8, fontweight='bold')

        # Label for Top part - Purple
        if econ_small > 100:
            ax1.text(x[i] + width / 2, econ_large + (econ_small / 2), f'${econ_small:,.0f}',
                     ha='center', va='center', fontsize=8, fontweight='bold')

        # Total on top of the whole Economy stack
        total_econ = econ_large + econ_small
        if total_econ > 0:
            ax1.text(x[i] + width / 2, total_econ + 100, f'${total_econ:,.0f}',
                     ha='center', va='bottom', fontsize=9, fontweight='bold', color='purple')

    ax1.set_ylabel(reverse_heb('סך הכנסות'), fontsize=12, fontweight='bold')
    ax1.set_title(reverse_heb('דו"ח הכנסות לפי יצרנית, מחלקה וגודל מטוס'), fontsize=16, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(manufacturers, fontsize=11)

    legend_elements = [
        Patch(facecolor=color_white, hatch=hatch_biz, edgecolor='black', label=reverse_heb('מחלקת עסקים')),
        Patch(facecolor=color_white, edgecolor='black', label=reverse_heb('אקונומי - מטוס גדול')),
        Patch(facecolor=color_small_econ, edgecolor='black', label=reverse_heb('אקונומי - מטוס קטן'))
    ]
    ax1.legend(handles=legend_elements, loc='upper left')
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    fig1.tight_layout()

# --- Visualization 2: Crew Flight Hours ---
if not df_crew.empty:
    df_crew['Full_Name'] = df_crew['First_Name'] + " " + df_crew['Last_Name']
    names_rev = [reverse_heb(name) for name in df_crew['Full_Name']]

    fig2, ax2 = plt.subplots(figsize=(16, 11))
    indices = np.arange(len(df_crew))

    color_short = '#3262E6'  # Blue
    color_long = '#E63946'  # Red

    ax2.bar(indices, df_crew['Short_Flight_Hours'], label=reverse_heb('טיסות קצרות'), color=color_short,
            edgecolor='black')
    ax2.bar(indices, df_crew['Long_Flight_Hours'], bottom=df_crew['Short_Flight_Hours'],
            label=reverse_heb('טיסות ארוכות'), color=color_long, edgecolor='black')

    # Data labels inside bars
    for i in range(len(df_crew)):
        short = df_crew.iloc[i]['Short_Flight_Hours']
        long = df_crew.iloc[i]['Long_Flight_Hours']
        total = short + long

        if short > 0.1:
            ax2.text(i, short / 2, f'{short:.1f}', ha='center', va='center', color='white', fontsize=8,
                     fontweight='bold')
        if long > 0.1:
            ax2.text(i, short + (long / 2), f'{long:.1f}', ha='center', va='center', color='white', fontsize=8,
                     fontweight='bold')

        if total > 0:
            ax2.text(i, total + 0.1, f'{total:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax2.set_xticks(indices)
    ax2.set_xticklabels(names_rev, rotation=45, ha='right', va='top', rotation_mode='anchor', fontsize=11,
                        fontweight='bold')

    for i, label in enumerate(ax2.get_xticklabels()):
        role = df_crew.iloc[i]['Role']
        if role == 'Pilot':
            label.set_color('blue')
        elif role == 'Attendant':
            label.set_color('green')
        else:
            label.set_color('black')

    ax2.set_ylabel(reverse_heb('סה"כ שעות טיסה'), fontsize=12, fontweight='bold')
    ax2.set_title(reverse_heb('שעות טיסה מצטברות לכלל אנשי צוות'), fontsize=16, fontweight='bold')

    custom_legend = [
        Patch(facecolor=color_short, label=reverse_heb('טיסות קצרות')),
        Patch(facecolor=color_long, label=reverse_heb('טיסות ארוכות')),
        Patch(facecolor='none', edgecolor='blue', label=reverse_heb('שם בכחול = טייס')),
        Patch(facecolor='none', edgecolor='green', label=reverse_heb('שם בירוק = דייל'))
    ]
    ax2.legend(handles=custom_legend, loc='upper right', frameon=True, shadow=True)

    plt.grid(axis='y', linestyle='--', alpha=0.5)
    fig2.tight_layout(pad=3.0)
    plt.subplots_adjust(bottom=0.25)

plt.show()