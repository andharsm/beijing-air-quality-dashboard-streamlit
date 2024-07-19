from unittest import result
import streamlit as st
import pandas as pd
import os
import datetime
from multiprocessing import Pool
import func
import google.generativeai as genai

# Load data
@st.cache_data
def load_data(dataset_csv, dataset_dir):
    dict_df = {}
    for file in dataset_csv:
        station = file[:-4]
        dict_df[station] = pd.read_csv(os.path.join(dataset_dir, file))
        dict_df[station]['datetime'] = pd.to_datetime(dict_df[station]['datetime'])
        dict_df[station].set_index('datetime', inplace=True)
    return dict_df

@st.cache_data
def predict_data(dict_df):
    with Pool() as pool:
        results = pool.map(func.process_single_df, dict_df.items())
    result_dict = {key: df for key, df in results}
    result_dict = func.cluster_aqi(result_dict, dict_df)
    result_dict = func.get_coord(result_dict)
    return result_dict

@st.cache_data
def get_gemini():
    genai.configure(api_key="AIzaSyAMBjo_Ea9DcWw2pKmiFKwpQEaxhjKoKMI")
    # Inisialisasi model atau tugas yang ingin Anda lakukan
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model

def main():
    st.title("Indeks Kualitas Udara (AQI) Beijing")

    dataset_csv = os.listdir('datasets')
    DATASET_DIR = 'datasets'

    dict_df = load_data(dataset_csv, DATASET_DIR)
    print('Load berhasil')

    last_datetime = dict_df['Aotizhongxin'].index[-1]
    last_date = last_datetime.date()
    last_time = last_datetime.time()

    start_date = last_date - datetime.timedelta(days=365)
    end_date = last_date

    col1, col2 = st.columns(2)

    with col1:
        tanggal = st.date_input('Tanggal', value=last_date, min_value=start_date, max_value=end_date)

    with col2:
        time_options = [datetime.time(hour=h) for h in range(24)]
        waktu = st.selectbox('Waktu', options=time_options, index=time_options.index(last_time))

    tanggal_dan_waktu = datetime.datetime.combine(tanggal, waktu)

    st.write('Terakhir diperbarui:', tanggal_dan_waktu)

    filtered_dict_df = {}
    for station, df in dict_df.items():
        filtered_dict_df[station] = df.loc[:tanggal_dan_waktu]

    # Ambil hasil prediksi dalam bentuk dictionary of DataFrames
    result_dict = predict_data(filtered_dict_df)


    # Untuk setiap DataFrame dalam dictionary, lakukan interpolasi
    for key, df in result_dict.items():
        # Identifikasi kolom yang mengandung '_avg' dan '_aqi'
        columns_to_interpolate = [col for col in df.columns if '_avg' in col or '_aqi' in col]
        
        # Interpolasi kolom yang telah diidentifikasi
        df[columns_to_interpolate] = df[columns_to_interpolate].interpolate(method='linear', limit_direction='both')

        # Update DataFrame yang sudah diinterpolasi kembali ke dictionary
        result_dict[key] = df

    # pilihan kota
    selected_district = st.selectbox('Distrik', list(dict_df.keys()))

    print('Data siap')

    st.markdown("""
    <style>
    .legend-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start; /* Align bars to the top */
        margin-bottom: 10px;
    }

    .legend-item {
        text-align: center;
        width: 120px; /* Adjust width as needed */
    }

    .box {
        width: 100%; /* Match width of the legend-item */
        height: 20px;
        margin-bottom: 5px;
    }

    .green {
        background-color: green;
    }

    .yellow {
        background-color: yellow;
    }

    .orange {
        background-color: orange;
    }

    .red {
        background-color: red;
    }

    .purple {
        background-color: purple;
    }

    .maroon {
        background-color: maroon;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="legend-container">
        <div class="legend-item">
            <div class="box green"></div>
            <span>Baik</span>
        </div>
        <div class="legend-item">
            <div class="box yellow"></div>
            <span>Sedang</span>
        </div>
        <div class="legend-item">
            <div class="box orange"></div>
            <span>Tidak Sehat<br>untuk Kelompok<br>Sensitif</span>
        </div>
        <div class="legend-item">
            <div class="box red"></div>
            <span>Tidak Sehat</span>
        </div>
        <div class="legend-item">
            <div class="box purple"></div>
            <span>Sangat Tidak<br>Sehat</span>
        </div>
        <div class="legend-item">
            <div class="box maroon"></div>
            <span>Berbahaya</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    status = func.get_status(result_dict[selected_district].iloc[-3]['AQI'])
    col1, col2 = st.columns(2)

    with col1:
      # Plot circular progress bar untuk stasiun yang dipilih (contoh 'Aotizhongxin')
      fig = func.plot_circular_progressbar(result_dict, selected_district)
      st.pyplot(fig)

    with col2:

        # Menampilkan simbol/ikon menggunakan HTML dan Font Awesome
        st.markdown("""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
            <div style="font-size:24px; line-height:2.3; padding-left: 10px;">
                <p style="margin: 10px 0;"><i class="fas fa-stream"></i> Status: {status}</p>
                <p style="margin: 10px 0;"><i class="fas fa-cloud"></i> Polutan Utama: {polutan}</p>
                <p style="margin: 10px 0;"><i class="fas fa-thermometer-half"></i> Suhu: {suhu}°C</p>
                <p style="margin: 10px 0;"><i class="fas fa-tint"></i> Titik Embun: {titik_embun}°C</p>
                <p style="margin: 10px 0;"><i class="fas fa-tachometer-alt"></i> Tekanan: {tekanan} hPa</p>
                <p style="margin: 10px 0;"><i class="fas fa-wind"></i> Kecepatan Angin: {kecepatan_angin} km/h</p>
                <p style="margin: 10px 0;"><i class="fas fa-compass"></i> Arah Angin: {arah_angin}</p>
            </div>
            """.format(status=status, polutan=result_dict[selected_district].iloc[-3]['pollutant_primary'], suhu=result_dict[selected_district].iloc[-3]['TEMP'], kecepatan_angin=result_dict[selected_district].iloc[-3]['WSPM'], titik_embun=result_dict[selected_district].iloc[-3]['DEWP'], arah_angin=result_dict[selected_district].iloc[-3]['wd'], tekanan=result_dict[selected_district].iloc[-3]['PRES']), unsafe_allow_html=True)

    polutan=result_dict[selected_district].iloc[-3]['pollutant_primary']
    suhu=result_dict[selected_district].iloc[-3]['TEMP']
    kecepatan_angin=result_dict[selected_district].iloc[-3]['WSPM']
    titik_embun=result_dict[selected_district].iloc[-3]['DEWP']
    arah_angin=result_dict[selected_district].iloc[-3]['wd']
    tekanan=result_dict[selected_district].iloc[-3]['PRES']

    # Inisialisasi model atau tugas yang ingin Anda lakukan
    model = get_gemini()

    text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut dan kondisi distrik dengan Status: {status}, \nPolutan Utama: {polutan}, suhu: {suhu}, titik embun: {titik_embun}, tekanan: {tekanan} kecepatan dan arah angin {arah_angin} {kecepatan_angin}'
    with st.expander("Analisa Gemini"):
        result = func.gemini_analyze(text, fig, model)
        st.write(result)

    st.header('Ikhtisar', divider='grey')

    ikhtisar = {'Status': [status],
                'Indeks Kualitas Udara': [result_dict[selected_district].iloc[-3]['AQI']],
                'Polutan Utama': [result_dict[selected_district].iloc[-3]['pollutant_primary']]}

    df_ikhtisar = pd.DataFrame(ikhtisar)

    st.dataframe(df_ikhtisar, hide_index=True, width=1000)
    
    fig = func.create_progress_bars(result_dict, selected_district)
    st.pyplot(fig)

    text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut'
    with st.expander("Analisa Gemini"):
        result = func.gemini_analyze(text, fig, model)
        st.write(result)

    st.header('Prakiraan', divider='grey')

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["AQI", "Suhu", "Titik Embun", "Tekanan", "Angin"])

    with tab1:
        fig = func.line_chart_aqi(result_dict, selected_district)
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada prakiraan aqi, data saat ini adalah data jam {waktu} dan xticks di 2 sebelah kanan dengan linechart berwarna hitam adalah prediksi di jam jam berikutnya'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result)

    with tab2:
        fig = func.line_chart_temp(result_dict, selected_district)
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada prakiraan suhu, data saat ini adalah data jam {waktu} dan xticks di 2 sebelah kanan dengan linechart berwarna hitam adalah prediksi di jam jam berikutnya'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result)

    with tab3:
        fig = func.line_chart_dewp(result_dict, selected_district)
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada prakiraan titik embun, data saat ini adalah data jam {waktu} dan xticks di 2 sebelah kanan dengan linechart berwarna hitam adalah prediksi di jam jam berikutnya'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result)

    with tab4:
        fig = func.line_chart_pres(result_dict, selected_district)
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada prakiraan tekanan, data saat ini adalah data jam {waktu} dan xticks di 2 sebelah kanan dengan linechart berwarna hitam adalah prediksi di jam jam berikutnya'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result)

    with tab5:
        fig = func.line_chart_wspm(result_dict, selected_district)
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada prakiraan arah dan kecepatan angin, data saat ini adalah data jam {waktu} dan xticks di 2 sebelah kanan dengan linechart berwarna hitam adalah prediksi di jam jam berikutnya'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result)    

    st.header('Riwayat AQI Polutan', divider='grey')

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"])

    with tab1:
        fig = func.aqi_barchart(result_dict, selected_district, 'PM2.5_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI PM2.5 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    with tab2:
        fig = func.aqi_barchart(result_dict, selected_district, 'PM10_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI PM10 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    with tab3:
        fig = func.aqi_barchart(result_dict, selected_district, 'SO2_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI SO2 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    with tab4:
        fig = func.aqi_barchart(result_dict, selected_district, 'NO2_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI NO2 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    with tab5:
        fig = func.aqi_barchart(result_dict, selected_district, 'CO_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI CO 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    with tab6:
        fig = func.aqi_barchart(result_dict, selected_district, 'O3_aqi')
        st.pyplot(fig)

        text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar berikut fokuslah untuk membahas variabel pada riwayat AQI O3 24 jam terakhir dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI'
        with st.expander("Analisa Gemini"):
            result = func.gemini_analyze(text, fig, model)
            st.write(result) 

    st.header('Peta Persebaran', divider='grey')
    
    @st.cache_data
    def display_map(tanggal_dan_waktu, result_dict):
        fig, df = func.geo_aqi_hourly(tanggal_dan_waktu, result_dict)
        return fig, df
    
    fig, df = display_map(tanggal_dan_waktu, result_dict)
    st.plotly_chart(fig)

    text = f'Sebagai profesional analisis, insight apa yang kamu dapatkan berdasarkan gambar geo map terhadap kondisi AQI berikut fokuslah untuk membahas variabel pada AQI dengan keterangan hijau adalah kondisi terbaik dan coklat berbahaya kamu dapat melihat panduan indeks AQI WHO terkait warna dan value AQI, sebagai detail ini data lengkapnya {df}'
    with st.expander("Analisa Gemini"):
        result = func.gemini_analyze(text, fig, model)
        st.write(result) 

if __name__ == '__main__':
    main()
