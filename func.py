import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import io
from PIL import Image
import plotly.io as pio

# Fungsi untuk menghitung modus
def mode(series):
    return series.mode()[0]

# Fungsi untuk memproses prediksi per DataFrame
def process_single_df(args):
    key, df = args
    df['hour'] = df.index.hour
    df['month_day'] = df.index.strftime('%m-%d')
    df['year'] = df.index.year

    average_values = df.groupby(['hour', 'month_day', 'year'])[['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'WSPM', 'RAIN']].mean()

    df['day'] = df.index.day
    df['month'] = df.index.month

    grouped_modes = df.groupby(['hour', 'day', 'month']).agg({
        'wd': mode,
        'station': mode
    })

    last_timestamp = df.index.max()
    forecast_start = last_timestamp + pd.Timedelta(hours=1)
    forecast_end = forecast_start + pd.DateOffset(hours=1)
    forecast_dates = pd.date_range(start=forecast_start, end=forecast_end, freq='h')

    df_predicted = pd.DataFrame(columns=['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'WSPM', 'RAIN', 'wd', 'station'])
    predicted_list = []

    for forecast_date in forecast_dates:
        forecast_hour = forecast_date.hour
        forecast_month_day = forecast_date.strftime('%m-%d')
        forecast_year = forecast_date.year
        forecast_datetime = pd.Timestamp(forecast_date)

        predicted_values = average_values.loc[(forecast_hour, forecast_month_day, slice(None)), :].mean()

        predicted_wd = grouped_modes.loc[(forecast_hour, forecast_datetime.day, forecast_datetime.month), 'wd']
        predicted_station = grouped_modes.loc[(forecast_hour, forecast_datetime.day, forecast_datetime.month), 'station']

        predicted_values['wd'] = predicted_wd
        predicted_values['station'] = predicted_station

        predicted_list.append(predicted_values)

    df_predicted = pd.DataFrame(predicted_list, index=forecast_dates)

    return key, df_predicted

    # Fungsi untuk menghitung AQI
def calculate_aqi(value, breakpoints):
    for bp in breakpoints:
        if bp[0] <= value <= bp[1]:
            aqi = ((bp[3] - bp[2]) / (bp[1] - bp[0])) * (value - bp[0]) + bp[2]
            return round(aqi)
    return None

def cluster_aqi(pred_dict_df, dict_df):
  result_df = {}

  # deep copy
  df_copy = pred_dict_df

  # variasi breakpoint berdasarkan polutan
  breakpoints = {
      'PM2.5': [
          (0, 12, 0, 50),
          (12.1, 35.4, 51, 100),
          (35.5, 55.4, 101, 150),
          (55.5, 150.4, 151, 200),
          (150.5, 250.4, 201, 300),
          (250.5, 350.4, 301, 500)
      ],
      'PM10': [
          (0, 54, 0, 50),
          (55, 154, 51, 100),
          (155, 254, 101, 150),
          (255, 354, 151, 200),
          (355, 424, 201, 300),
          (425, 504, 301, 500)
      ],
      'SO2': [
          (0, 35, 0, 50),
          (36, 75, 51, 100),
          (76, 185, 101, 150),
          (186, 304, 151, 200),
          (305, 604, 201, 300),
          (605, 804, 301, 500)
      ],
      'NO2': [
          (0, 53, 0, 50),
          (54, 100, 51, 100),
          (101, 360, 101, 150),
          (361, 649, 151, 200),
          (650, 1249, 201, 300),
          (1250, 1649, 301, 500)
      ],
      'CO': [
          (0, 4.4, 0, 50),
          (4.5, 9.4, 51, 100),
          (9.5, 12.4, 101, 150),
          (12.5, 15.4, 151, 200),
          (15.5, 30.4, 201, 300),
          (30.5, 40.4, 301, 500)
      ],
      'O3': [
          (0, 0.054, 0, 50),
          (0.055, 0.070, 51, 100),
          (0.071, 0.085, 101, 150),
          (0.086, 0.105, 151, 200),
          (0.106, 0.200, 201, 300),
          (0.201, 0.604, 301, 500)
      ]
  }

  for key in df_copy:
    df = df_copy[key]

    base_df = dict_df[key][['PM2.5', 'PM10', 'CO', 'O3', 'SO2', 'NO2', 'TEMP', 'PRES', 'DEWP', 'WSPM', 'RAIN', 'wd', 'station']]

    # concat dengan data dict_df 24 jam terakhir
    df = pd.concat([base_df, df])

    # avg 24 hours
    df['PM2.5_avg'] = df['PM2.5'].rolling(window=24, min_periods=1).mean().round(2)
    df['PM10_avg'] = df['PM10'].rolling(window=24, min_periods=1).mean().round(2)

    # avg 8 hours
    df['CO_avg'] = df['CO'].rolling(window=8, min_periods=1).mean().round(3)
    df['O3_avg'] = df['O3'].rolling(window=8, min_periods=1).mean().round(3)

    # avg 1 hours
    df['SO2_avg'] = df['SO2'].rolling(window=1, min_periods=1).mean().round(2)
    df['NO2_avg'] = df['NO2'].rolling(window=1, min_periods=1).mean().round(2)

    # Iterasi dan hitung AQI untuk setiap kolom polutan
    for pollutant in df.columns:
        if pollutant.endswith('_avg'):  # Pastikan hanya kolom rata-rata yang diproses
            pollutant_name = pollutant.split('_avg')[0]
            df[f'{pollutant_name}_aqi'] = df[pollutant].apply(lambda x: calculate_aqi(x, breakpoints[pollutant_name]))

    # Filter kolom-kolom yang berakhiran dengan _aqi
    aqi_columns = df.filter(regex='_aqi')

    # Dapatkan nilai maksimum dari setiap baris
    df['AQI'] = aqi_columns.max(axis=1)

    # Tentukan polutan utama berdasarkan nilai maksimum
    df['pollutant_primary'] = aqi_columns.idxmax(axis=1).apply(lambda x: x.split('_')[0])

    result_df[key] = df

  return result_df

# menambahkan data lokasi long dan lat
coordinates = {
    'Wanliu': (39.9893129, 116.2894284),
    'Shunyi': (40.1487504, 116.6538745),
    'Gucheng': (39.9061423, 116.1844475),
    'Dongsi': (39.9292472, 116.4177314),
    'Changping': (40.2196456, 116.2250912),
    'Tiantan': (39.8878583, 116.3928958),
    'Huairou': (40.3154808, 116.626028),
    'Aotizhongxin': (39.9888, 116.3985),
    'Nongzhanguan': (39.9433949, 116.4642027),
    'Wanshouxigong': (39.8899, 116.3525),
    'Dingling': (40.2944948, 116.21703999537226),
    'Guanyuan': (39.9322, 116.3567)
}

def get_coord(dict_df):
  # Pisahkan coordinates menjadi latitude dan longitude
  latitude = {station: coords[0] for station, coords in coordinates.items()}
  longitude = {station: coords[1] for station, coords in coordinates.items()}

  # Tambahkan kolom Latitude dan Longitude ke dataframe
  for key in dict_df:
    dict_df[key]['lat'] = dict_df[key]['station'].map(latitude)
    dict_df[key]['long'] = dict_df[key]['station'].map(longitude)

  return dict_df

def get_aqi_color(aqi):
    if aqi <= 50:
        return "green"
    elif aqi <= 100:
        return "yellow"
    elif aqi <= 150:
        return "orange"
    elif aqi <= 200:
        return "red"
    elif aqi <= 300:
        return "purple"
    else:
        return "maroon"

def get_status(aqi):
    if aqi <= 50:
        return 'Baik'
    elif aqi<= 100:
        return 'Sedang'
    elif aqi <= 150:
        return 'Tidak Sehat untuk Kelompok Sensitif'
    elif aqi <= 200:
        return 'Tidak Sehat'
    elif aqi <= 300:
        return 'Sangat Tidak Sehat'
    else:
        return 'Berbahaya'

# Fungsi untuk memplot circular progress bar
def plot_circular_progressbar(dict_df, key):
    df = dict_df[key].iloc[-3]
    value = df['AQI'].round()
    max_value = 500
    percentage = (value / max_value) * 100
    color = get_aqi_color(value)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(aspect="equal"))
    wedges, _ = ax.pie([percentage, 100-percentage], startangle=90, counterclock=False, colors=[color, "#e0e0e0"], wedgeprops=dict(width=0.3))
    ax.text(0, 0, f'{value}', horizontalalignment='center', verticalalignment='center', fontsize=40, weight='bold', color='#333333')
    centre_circle = plt.Circle((0, 0), 0.70, color='white', fc='white', linewidth=0)
    fig.gca().add_artist(centre_circle)
    plt.title(f'Indeks Kualitas Udara (AQI) {key}')
    plt.axis('equal')
    plt.tight_layout()

    return fig

def get_satuan(polutan):
  if polutan == 'PM2.5':
    return 'μg/m3'
  elif polutan == 'PM10':
    return 'μg/m3'
  elif polutan == 'SO2':
    return 'ppb'
  elif polutan == 'NO2':
    return 'ppb'
  elif polutan == 'CO':
    return 'ppm'
  elif polutan == 'O3':
    return 'ppm'
  else:
    return None

def create_progress_bars(dict_df, key):
    
    df = dict_df[key]

    # df baris ketiga dari bawah
    df = df.iloc[-3]

    labels = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3']
    values = df[['PM2.5_aqi', 'PM10_aqi', 'SO2_aqi', 'NO2_aqi', 'CO_aqi', 'O3_aqi']].values.tolist()
    concents = df[['PM2.5_avg', 'PM10_avg', 'SO2_avg', 'NO2_avg', 'CO_avg', 'O3_avg']].values.tolist()
    max_value = 500

    # Menghitung persentase nilai terhadap nilai maksimum
    percentages = [value / max_value for value in values]

    # Membalik urutan labels, values, dan percentages
    labels.reverse()
    values.reverse()
    percentages.reverse()
    concents.reverse()

    # Membuat figure dan axis
    fig, ax = plt.subplots(figsize=(8, 4))

    # Mengatur jarak antar progress bar
    bar_height = 0.3
    bar_spacing = 0.1

    # Menambahkan teks "Polutan" di atas label
    ax.text(-0.1, len(labels), 'Polutan', ha='left', va='center', fontsize=12)

    # Menambahkan teks "AQI" di atas nilai
    ax.text(1.03, len(labels), 'AQI', ha='left', va='center', fontsize=12)

    # Menambahkan teks "Konsentrasi" di atas nilai
    ax.text(1.35, len(labels), 'Konsentrasi', ha='right', va='center', fontsize=12)

    for i, (percentage, label, value, concent) in enumerate(zip(percentages, labels, values, concents)):
        # menyesuaikan warna dengan aqi color
        color = get_aqi_color(value)

        # get satuan
        satuan = get_satuan(label)

        # Membuat progress bar
        ax.barh([i], [percentage], color=color, height=bar_height, align='center')
        ax.barh([i], [1], color=color, height=bar_height, align='center', alpha=0.2)

        # Menampilkan label
        ax.text(-0.1, i, label, ha='left', va='center', fontsize=12)

        # Menampilkan nilai di sebelah kanan progress bar
        ax.text(1.03, i, f'{value}', ha='left', va='center', fontsize=12)

        # Menampilkan concent di sebelah kanan progress bar
        ax.text(1.35, i, f'{concent} {satuan}', ha='right', va='center', fontsize=12)

    # Mengatur sumbu dan label
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, len(labels) - 0.5)
    ax.set_yticks([])
    ax.set_xticks([])

    # Menghilangkan sumbu
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    return fig

def line_chart_aqi(dict_df, key):
    df = dict_df[key]

    # Memastikan index adalah datetime
    df.index = pd.to_datetime(df.index)

    # Mengambil data 7 jam terakhir
    df = df.iloc[-7:]

    # Membuat list time yang berisi kumpulan jam(H) pada dataset dan list aqi
    time = df.index.strftime('%H:%M').tolist()
    aqi = df['AQI'].tolist()

    # Membuat dataframe baru
    df = pd.DataFrame({'time': time, 'aqi': aqi})

    # Menyimpan nilai time pada indeks -3
    value_time = df.iloc[-3]['time']

    # Membuat plot
    fig, ax = plt.subplots(figsize=(10, 3))

    # Plot untuk data oranye (dari awal sampai -2)
    ax.plot(df["time"][:-2], df["aqi"][:-2], color='orange', linewidth=2)
    # Plot untuk data abu-abu (2 jam terakhir)
    ax.plot(df["time"][-3:], df["aqi"][-3:], color='gray', linewidth=2)

    # Mengisi area di bawah garis oranye
    ax.fill_between(df["time"][:-2], df["aqi"][:-2], color='orange', alpha=0.1)
    # Mengisi area di bawah garis abu-abu
    ax.fill_between(df["time"][-3:], df["aqi"][-3:], color='gray', alpha=0.1)

    # Menambahkan label pada setiap titik data sedikit di atas titik
    for i, txt in enumerate(df["aqi"]):
        ax.text(df["time"][i], df["aqi"][i]+3, str(txt), fontsize=12, ha='center')  # Menambahkan offset 3 untuk menggeser ke atas

    # Menyesuaikan rentang sumbu y dinamis
    min_aqi = min(aqi)
    max_aqi = max(aqi)
    y_lower = min_aqi - 5 if min_aqi > 5 else 0
    y_upper = max_aqi + 5

    ax.set_ylim(y_lower, y_upper)

    # Menghapus koordinat y dan grid, serta menghilangkan garis sumbu y atas dan kanan
    ax.set_yticks([])
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    aqi_value_at_value_time = df.loc[df["time"] == str(value_time), "aqi"].values[0]
    ax.plot([str(value_time), str(value_time)], [y_lower, aqi_value_at_value_time], color='gray', linestyle='--')

    # judul plot
    ax.set_title(f'Prakiraan Indeks Kualitas Udara (AQI) {key}')

    return fig


def line_chart_temp(dict_df, key):
    # Deep copy
    df = dict_df[key]

    # Memastikan index adalah datetime
    df.index = pd.to_datetime(df.index)

    # Mengambil data 7 jam terakhir
    df = df.iloc[-7:]

    # Membuat list time yang berisi kumpulan jam(H) pada dataset dan list temp
    time = df.index.strftime('%H:%M').tolist()
    temp = df['TEMP'].round(1).tolist()

    # Membuat dataframe baru
    df = pd.DataFrame({'time': time, 'temp': temp})

    # Menyimpan nilai time pada indeks -3
    value_time = df.iloc[-3]['time']

    # Membuat plot
    fig, ax = plt.subplots(figsize=(10, 3))

    # Plot untuk data hijau (dari awal sampai -3)
    ax.plot(df["time"][:-2], df["temp"][:-2], color='green', linewidth=2)
    # Plot untuk data abu-abu (2 jam terakhir)
    ax.plot(df["time"][-3:], df["temp"][-3:], color='gray', linewidth=2)

    # Mengisi area di bawah garis hijau
    ax.fill_between(df["time"][:-2], df["temp"][:-2], color='green', alpha=0.1)
    # Mengisi area di bawah garis abu-abu
    ax.fill_between(df["time"][-3:], df["temp"][-3:], color='gray', alpha=0.1)

    # Menambahkan label pada setiap titik data sedikit di atas titik
    for i, txt in enumerate(df["temp"]):
      if txt > 0:
        ax.text(df["time"][i], df["temp"][i] + 0.5, str(txt) + '°', fontsize=12, ha='center')
      else:
        ax.text(df["time"][i], df["temp"][i] - 1.5, str(txt) + '°', fontsize=12, ha='center')
    
    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    temp_value_at_value_time = df.loc[df["time"] == str(value_time), "temp"].values[0]
    
    # Menyesuaikan rentang sumbu y dinamis
    min_temp = min(temp)
    max_temp = max(temp)
    y_lower = min_temp - 3 if min_temp > 0 else min_temp - 3  # Mengatur sumbu y dimulai dari nilai min_temp - 2
    y_upper = max_temp + 2

    ax.set_ylim(y_lower, y_upper)

    # Menghapus koordinat y dan grid, serta menghilangkan garis sumbu y atas dan kanan
    ax.set_yticks([])
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    temp_value_at_value_time = df.loc[df["time"] == str(value_time), "temp"].values[0]
    if temp_value_at_value_time > 0:
        ax.plot([str(value_time), str(value_time)], [y_lower, temp_value_at_value_time], color='gray', linestyle='--')
    else:
        ax.plot([str(value_time), str(value_time)], [y_upper, temp_value_at_value_time], color='gray', linestyle='--')

    # judul fontweight='bold'
    ax.set_title(f'Prakiraan Suhu (Celcius) {key}')

    return fig

# line chart pres
def line_chart_pres(dict_df, key):
    # Deep copy
    df = dict_df[key]

    # Memastikan index adalah datetime
    df.index = pd.to_datetime(df.index)

    # Mengambil data 7 jam terakhir
    df = df.iloc[-7:]

    # Membuat list time yang berisi kumpulan jam(H) pada dataset dan list pres
    time = df.index.strftime('%H:%M').tolist()
    pres = df['PRES'].round(1).tolist()

    # Membuat dataframe baru
    df = pd.DataFrame({'time': time, 'pres': pres})

    # Menyimpan nilai time pada indeks -3
    value_time = df.iloc[-3]['time']

    # Membuat plot
    fig, ax = plt.subplots(figsize=(10, 3))

    # Plot untuk data hijau (dari awal sampai -3)
    ax.plot(df["time"][:-2], df["pres"][:-2], color='brown', linewidth=2)
    # Plot untuk data abu-abu (2 jam terakhir)
    ax.plot(df["time"][-3:], df["pres"][-3:], color='gray', linewidth=2)

    # Mengisi area di bawah garis hijau
    ax.fill_between(df["time"][:-2], df["pres"][:-2], color='brown', alpha=0.1)
    # Mengisi area di bawah garis abu-abu
    ax.fill_between(df["time"][-3:], df["pres"][-3:], color='gray', alpha=0.1)

    # Menambahkan label pada setiap titik data sedikit di atas titik
    for i, txt in enumerate(df["pres"]):
      if txt > 0:
        ax.text(df["time"][i], df["pres"][i] + 0.5, str(txt) + '°', fontsize=12, ha='center')
      else:
        ax.text(df["time"][i], df["pres"][i] - 1.5, str(txt) + '°', fontsize=12, ha='center')

    # Menyesuaikan rentang sumbu y dinamis
    min_pres = min(pres)
    max_pres = max(pres)
    y_lower = min_pres - 3 if min_pres > 0 else min_pres - 3  # Mengatur sumbu y dimulai dari nilai min_pres - 2
    y_upper = max_pres + 2

    ax.set_ylim(y_lower, y_upper)

    # Menghapus koordinat y dan grid, serta menghilangkan garis sumbu y atas dan kanan
    ax.set_yticks([])
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    pres_value_at_value_time = df.loc[df["time"] == str(value_time), "pres"].values[0]
    ax.plot([str(value_time), str(value_time)], [y_lower, pres_value_at_value_time], color='gray', linestyle='--')

    # judul fontweight='bold'
    ax.set_title(f'Prakiraan Tekanan (hPa) {key}')

    # Menampilkan plot
    return fig


# line chart dewp
def line_chart_dewp(dict_df, key):
    # Deep copy
    df = dict_df[key]

    # Memastikan index adalah datetime
    df.index = pd.to_datetime(df.index)

    # Mengambil data 7 jam terakhir
    df = df.iloc[-7:]

    # Membuat list time yang berisi kumpulan jam(H) pada dataset dan list dewp
    time = df.index.strftime('%H:%M').tolist()
    dewp = df['DEWP'].round(1).tolist()

    # Membuat dataframe baru
    df = pd.DataFrame({'time': time, 'dewp': dewp})

    # Menyimpan nilai time pada indeks -3
    value_time = df.iloc[-3]['time']

    # Membuat plot
    fig, ax = plt.subplots(figsize=(10, 3))

    # Plot untuk data hijau (dari awal sampai -3)
    ax.plot(df["time"][:-2], df["dewp"][:-2], color='blue', linewidth=2)
    # Plot untuk data abu-abu (2 jam terakhir)
    ax.plot(df["time"][-3:], df["dewp"][-3:], color='gray', linewidth=2)

    # Mengisi area di bawah garis hijau
    ax.fill_between(df["time"][:-2], df["dewp"][:-2], color='blue', alpha=0.1)
    # Mengisi area di bawah garis abu-abu
    ax.fill_between(df["time"][-3:], df["dewp"][-3:], color='gray', alpha=0.1)

    # Menambahkan label pada setiap titik data sedikit di atas titik
    for i, txt in enumerate(df["dewp"]):
      if txt > 0:
        ax.text(df["time"][i], df["dewp"][i] + 0.5, str(txt) + '°', fontsize=12, ha='center')
      else:
        ax.text(df["time"][i], df["dewp"][i] - 1.5, str(txt) + '°', fontsize=12, ha='center')

    # Menyesuaikan rentang sumbu y dinamis
    min_dewp = min(dewp)
    max_dewp = max(dewp)
    y_lower = min_dewp - 3 if min_dewp > 0 else min_dewp - 3  # Mengatur sumbu y dimulai dari nilai min_dewp - 2
    y_upper = max_dewp + 2

    ax.set_ylim(y_lower, y_upper)

    # Menghapus koordinat y dan grid, serta menghilangkan garis sumbu y atas dan kanan
    ax.set_yticks([])
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    dewp_value_at_value_time = df.loc[df["time"] == str(value_time), "dewp"].values[0]
    if dewp_value_at_value_time > 0:
        ax.plot([str(value_time), str(value_time)], [y_lower, dewp_value_at_value_time], color='gray', linestyle='--')
    else:
        ax.plot([str(value_time), str(value_time)], [y_upper, dewp_value_at_value_time], color='gray', linestyle='--')

    # judul fontweight='bold'
    ax.set_title(f'Prakiraan Titik Embun (celcius) {key}')

    # Menampilkan plot
    return fig


def get_direct(direction):
    direction_map = {
        'N': '↑', 'NNE': '↗', 'NE': '↗', 'ENE': '↗',
        'E': '→', 'ESE': '↘', 'SE': '↘', 'SSE': '↘',
        'S': '↓', 'SSW': '↙', 'SW': '↙', 'WSW': '↙',
        'W': '←', 'WNW': '↖', 'NW': '↖', 'NNW': '↖'
    }
    return direction_map.get(direction, '')

def line_chart_wspm(dict_df, key):
    # Deep copy
    df = dict_df[key]

    # Memastikan index adalah datetime
    df.index = pd.to_datetime(df.index)

    # Mengambil data 7 jam terakhir
    df = df.iloc[-7:]

    # Membuat list time yang berisi kumpulan jam(H) pada dataset dan list wspm
    time = df.index.strftime('%H:%M').tolist()
    wspm = df['WSPM'].round(1).tolist()
    direct = df['wd'].apply(get_direct).tolist()

    # Membuat dataframe baru
    df = pd.DataFrame({'time': time, 'wspm': wspm, 'direct': direct})

    # Menyimpan nilai time pada indeks -3
    value_time = df.iloc[-3]['time']

    # Membuat plot
    fig, ax = plt.subplots(figsize=(10, 3))

    # Plot untuk data hijau (dari awal sampai -3)
    ax.plot(df["time"][:-2], df["wspm"][:-2], color='skyblue', linewidth=2)
    # Plot untuk data abu-abu (2 jam terakhir)
    ax.plot(df["time"][-3:], df["wspm"][-3:], color='gray', linewidth=2)

    # Mengisi area di bawah garis hijau
    ax.fill_between(df["time"][:-2], df["wspm"][:-2], color='skyblue', alpha=0.1)
    # Mengisi area di bawah garis abu-abu
    ax.fill_between(df["time"][-3:], df["wspm"][-3:], color='gray', alpha=0.1)

    # Menambahkan label dan wind direct pada setiap titik data sedikit di atas titik
    for i, txt in enumerate(df["wspm"]):
        if txt > 0:
            ax.text(df["time"][i], df["wspm"][i] + 0.5, f"{txt} m/s", fontsize=12, ha='center')
            ax.text(df["time"][i], df["wspm"][i] + 0.8, df["direct"][i], fontsize=12, ha='center')
        else:
            ax.text(df["time"][i], df["wspm"][i] - 1.5, f"{txt} m/s", fontsize=12, ha='center')
            ax.text(df["time"][i], df["wspm"][i] - 1.8, df["direct"][i], fontsize=12, ha='center')

    # Menyesuaikan rentang sumbu y dinamis
    min_wspm = min(wspm)
    max_wspm = max(wspm)
    y_lower = min_wspm - 1
    y_upper = max_wspm + 1

    ax.set_ylim(y_lower, y_upper)

    # Menghapus koordinat y dan grid, serta menghilangkan garis sumbu y atas dan kanan
    ax.set_yticks([])
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Menambahkan garis putus-putus pada titik waktu value_time yang menyentuh titik line chart
    wspm_value_at_value_time = df.loc[df["time"] == str(value_time), "wspm"].values[0]
    ax.plot([str(value_time), str(value_time)], [y_lower, wspm_value_at_value_time], color='gray', linestyle='--')

    # judul
    ax.set_title(f'Prakiraan Kecepatan (m/s) dan Arah Angin {key}')

    # Menampilkan plot
    return fig

def aqi_barchart(df, key, polutan):
    # Ensure we have the correct datetime index
    df = df[key][[polutan]].iloc[-26:-2]
    
    # Extract the values and the corresponding timestamps
    values = df[polutan].astype(int).values
    time_index = df.index.strftime('%H:%M')

    min_val = min(values)

    # Create the bar chart
    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.bar(range(24), values, color=[get_aqi_color(aqi) for aqi in values])

    # Add value labels on top of each bar
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + min_val*0.01, round(yval, 2), ha='center', va='bottom')

    # Set the x-ticks to the time index
    ax.set_xticks(range(24))
    ax.set_xticklabels(time_index, rotation=45, ha='right')

    # Menyesuaikan rentang sumbu y dinamis
    min_values = min(values)
    max_values = max(values)
    y_lower = min_values - 1
    y_upper = max_values + 1

    ax.set_ylim(y_lower, y_upper)

    # Remove top, left, and right borders
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    polutan = polutan[:-4]

    ax.set_title(f'Riwayat AQI {polutan} 24 Jam Terakhir')

    return fig

df_geo = {'station': [],
                'lat': [],
                'long': [],
                'AQI': [],
                'pollutant_primary': []
                }

def geo_aqi_hourly(datetime=None, result_dict=None, df_geo=df_geo):
    
    for key in result_dict:
        df = result_dict[key][['station','lat','long', 'AQI', 'pollutant_primary']]
        df = df.loc[datetime]

        df_geo['station'].append(df['station'])
        df_geo['lat'].append(df['lat'])
        df_geo['long'].append(df['long'])
        df_geo['AQI'].append(df['AQI'])
        df_geo['pollutant_primary'].append(df['pollutant_primary'])
        
    df_geo = pd.DataFrame(df_geo)

    df_geo['status'] = df_geo['AQI'].apply(get_status)        
    df_geo['Color'] = df_geo['AQI'].apply(get_aqi_color)

    # Konversi lat dan long ke numpy array untuk menghitung mean
    center_lat = df_geo['lat'].mean()
    center_lon = df_geo['long'].mean()

    # Buat peta menggunakan Plotly
    fig = px.scatter_mapbox(
        df_geo,
        lat='lat',
        lon='long',
        color='Color',
        color_discrete_map={
            "green": "Green",
            "yellow": "Yellow",
            "orange": "Orange",
            "red": "Red",
            "purple": "Purple",
            "maroon": "Maroon"
        },
        hover_name='station',
        hover_data={
            'AQI': True,  # Tampilkan AQI
            'pollutant_primary': True,  # Tampilkan polutan utama
            'status': True,  # Tampilkan cluster
            'lat': False,  # Sembunyikan atribut latitude
            'long': False, # Sembunyikan atribut longitude
            'Color': False  # Sembunyikan atribut warna
        },
        zoom=9,
        height=600,
        title="Distribusi AQI di Distrik Beijing"
    )

    # Menyembunyikan legend dan atur ukuran titik
    fig.update_traces(marker=dict(size=30), showlegend=False)

    # Atur pusat peta
    fig.update_layout(mapbox_style="open-street-map", mapbox_center={"lat": center_lat, "lon": center_lon})
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})# Konversi lat dan long ke numpy array untuk menghitung mean

    return fig, df_geo

def gemini_analyze(text, fig, model):
    try:
        # Convert the matplotlib figure to a PIL Image
        if hasattr(fig, 'write_image'):
            # Plotly figure, convert to PIL Image
            buf = io.BytesIO()
            pio.write_image(fig, buf, format='png')
            buf.seek(0)
            pil_image = Image.open(buf)
        else:
            # Matplotlib figure, directly convert to PIL Image
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            pil_image = Image.open(buf)

        response_gemini = model.generate_content([text, pil_image], stream=False)
        response_gemini.resolve()
        result = response_gemini.text
        return result

    except Exception as e:
        return f"An error occurred: {e}"