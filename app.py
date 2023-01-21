import streamlit as st
import sqlite3 as sq
import pandas as pd
import numpy as np
from streamlit_option_menu import option_menu
import requests
from streamlit_lottie import st_lottie
import xlsxwriter
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb
import streamlit.components.v1 as components
import base64
from pathlib import Path
from PIL import Image
import plost

st.set_page_config(
    page_title="CoVar",
    page_icon="resources/icon.png",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None
    )

hide_menu_style= '''
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            '''
st.markdown(hide_menu_style, unsafe_allow_html=True)

#sitemenu
selected = option_menu(
    menu_title=None,
    options=["Home", "DB", "About", "Help"],
    icons=["house", "clipboard-data", "info-circle", "question-circle"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#fafafa"},
        "icon": {"color": "orange", "font-size": "25px"}, 
        "nav-link": {
            "font-size": "25px",
            "text-align": "left",
            "margin":"0px",
            "--hover-color": "#eee"
        },
        "nav-link-selected": {"background-color": "green"},
    }

)

#lottie implementation
def load_lottieurl(url: str):
    r = requests.get(url)
    return r.json()

#home page
if selected == "Home":
    st.markdown("---")
    col1, col2, col3 = st.columns (3)
    with col2:
        st.subheader("**Welcome to CoVar!**")
    dbcol1, dbcol2, dbcol3 = st.columns([1,3,1])
    with dbcol2:
        url = "https://assets5.lottiefiles.com/packages/lf20_cwhdHu.json"
        home_json = load_lottieurl(url)
        st_lottie(home_json)
        st.caption("Molecular and Epidemilogical Database for Major SARS-CoV-2 Variants")

#DB
elif selected == "DB":
    st.markdown("---")
    dbcol1, dbcol2, dbcol3 = st.columns([1,4,1])
    with dbcol2:
        url = "https://assets5.lottiefiles.com/packages/lf20_8axjdnts.json"
        db_json = load_lottieurl(url)
        st_lottie(db_json)

    st.markdown("**Search by :orange[_Pango Lineage_]:**")
    lineage = st.text_input(
    "Enter the Pango Lineage Here: (e.g., B.1.617.2)",
    max_chars=20,
    ).upper()

    with st.expander("Alternatively you can search by WHO Label down below:"):
        label = st.text_input(
        "Enter the WHO Label Here: (e.g., Gamma)",
        max_chars=20,
        ).lower().capitalize()

    if lineage:
        con=sq.connect('db/covar.db')
        cur=con.cursor()
        sql_lineage = (lineage,)
        lineage_checker = cur.execute('''
            SELECT * FROM covar WHERE Pango_Lineage=?
             ''',sql_lineage)
        if not lineage_checker.fetchone():
            st.error("Pango lineage not found!", icon="🚨")
            con.close()
        else:
            st.title(lineage)
            dbcol1, dbcol2, dbcol3 = st.columns(3)
            with dbcol2:
                st.subheader("General Info")

            myrows=[
            list(row) for row in cur.execute('''
            SELECT Pango_Lineage, WHO_Label, First_Country, First_Date, VOC FROM covar WHERE Pango_Lineage=?
             ''',sql_lineage)
            ]
            st.dataframe(
            pd.DataFrame(
            myrows, 
            columns=["Pango Lineage", "WHO Label", "First Detected Country", "First Detected Date", "WHO Monitoring Status"]
            ).iloc[:1] 
            ) 

            st.markdown("---")
            dbcol1, dbcol2, dbcol3 = st.columns(3)
            with dbcol2:
                st.subheader("Molecular Info")
            col1, col2 = st.columns(2)   
            with col1:
                myrows_mol=[
                list(row) for row in cur.execute('''
                SELECT Mutation_N, Mutation_A FROM covar WHERE Pango_Lineage=?
                ''',sql_lineage)
                ]
            
                molecular_info = pd.DataFrame(
                myrows_mol, 
                columns=["Nucleotide Mutation", "Amino Acid Mutation"]
                )
            
                st.dataframe(molecular_info, width=600) 

                #excel downloader
                def to_excel(df):
                    output = BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    workbook = writer.book
                    worksheet = writer.sheets['Sheet1']
                    format1 = workbook.add_format({'num_format': '0.00'}) 
                    worksheet.set_column('A:A', None, format1)  
                    writer.save()
                    processed_data = output.getvalue()
                    return processed_data
                mutations_xlsx = to_excel(molecular_info)
                st.download_button(
                label='📥 Click to download mutations as an Excel file',
                data=mutations_xlsx ,
                file_name= f"{lineage} mutations.xlsx"
                )

            #pdb viewer
            with col2:
                
                (chart_id, pdb_id) = cur.execute('''
                SELECT Pango_lineage, Spike_PDB FROM covar WHERE Pango_Lineage=?
                ''',sql_lineage).fetchone()
                
                st.text(f"{lineage} Spike Protein:")
                components.html('''
                <script src="https://3Dmol.org/build/3Dmol-min.js"></script>     
                <script src="https://3Dmol.org/build/3Dmol.ui-min.js"></script>     

                <div style="height: 400px; width: 400px; position: relative;" class='viewer_3Dmoljs' data-pdb={} data-style1='cartoon:color=spectrum' data-backgroundcolor='0xffffff' data-style='stick' data-spin='axis:y;speed:1'></div>       
                '''.format(pdb_id), width=500 ,height=500 )

            #mutation_chart svg
            mutation_chart_location = f"resources/{chart_id}.svg"
            def render_svg(svg):
                #Renders the given svg string."""
                b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
                html = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
                st.write(html, unsafe_allow_html=True)

            f = open(mutation_chart_location,"r")
            lines = f.readlines()
            line_string=''.join(lines)

            st.caption(f"Mutation chart of the {lineage} genome:")
            render_svg(line_string)
            
            st.markdown("---")
            subcol1, subcol2, subcol3 = st.columns(3)
            with subcol2:
                st.subheader("Epidemilogical_Info")
            
            #countries
            (v1, v2, v3, v4, v5, v6) = cur.execute('''
                    SELECT Value1, Value2, Value3, Value4, Value5, Other FROM covar WHERE Pango_Lineage=?
                    ''',sql_lineage).fetchone()
            (c1, c2, c3, c4, c5) =  cur.execute('''
                    SELECT Country1, Country2, Country3, Country4, Country5 FROM covar WHERE Pango_Lineage=?
                    ''',sql_lineage).fetchone()  
            c6 = "Other"  

            country_info = pd.DataFrame(
                                    {'Country': [c1, c2, c3, c4, c5, c6],
                                    'Percentage': [v1, v2, v3, v4, v5, v6]}
                                       )   
            
            epicol1, epicol2 = st.columns(2)
            with epicol1:
                st.dataframe(country_info)

            with epicol2:    
                with st.container():
                    plost.donut_chart(country_info, "Country","Percentage"
                                     ,legend="right", use_container_width=True)
            subepicol1, subepicol2, subepicol3 = st.columns([1,2,1])
            with subepicol2:
                st.caption("Percentage of cases in top 5 countries with the most cases")        


            con.close()

    elif label:
        con=sq.connect('db/covar.db')
        cur=con.cursor()
        sql_label =(label,)
        label_checker = cur.execute('''
            SELECT * FROM covar WHERE WHO_Label=?
             ''',sql_label)
        if not label_checker.fetchone():
            st.error("Variant not found!", icon="🚨")
            con.close()
        else:
            st.title(label)
            dbcol1, dbcol2, dbcol3 = st.columns(3)
            with dbcol2:
                st.subheader("General Info")

            myrows=[
            list(row) for row in cur.execute('''
            SELECT Pango_Lineage, WHO_Label, First_Country, First_Date, VOC FROM covar WHERE WHO_Label=?
             ''',sql_label)
            ]
            st.dataframe(
            pd.DataFrame(
            myrows, 
            columns=["Pango Lineage", "WHO Label", "First Detected Country", "First Detected Date", "WHO Monitoring Status"]
            ).iloc[:1] 
            ) 

            st.markdown("---")
            dbcol1, dbcol2, dbcol3 = st.columns(3)
            with dbcol2:
                st.subheader("Molecular Info")
            col1, col2 = st.columns(2)   
            with col1:
                myrows_mol=[
                list(row) for row in cur.execute('''
                SELECT Mutation_N, Mutation_A FROM covar WHERE WHO_Label=?
                ''',sql_label)
                ]
            
                molecular_info = pd.DataFrame(
                myrows_mol, 
                columns=["Nucleotide Mutation", "Amino Acid Mutation"]
                )
            
                st.dataframe(molecular_info, width=600) 

                #excel downloader
                def to_excel(df):
                    output = BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                    workbook = writer.book
                    worksheet = writer.sheets['Sheet1']
                    format1 = workbook.add_format({'num_format': '0.00'}) 
                    worksheet.set_column('A:A', None, format1)  
                    writer.save()
                    processed_data = output.getvalue()
                    return processed_data
                mutations_xlsx = to_excel(molecular_info)
                st.download_button(
                label='📥 Click to download mutations as an Excel file',
                data=mutations_xlsx ,
                file_name= f"{label} mutations.xlsx"
                )


            #pdb viewer
            with col2:
                
                (chart_id, pdb_id) = cur.execute('''
                SELECT Pango_lineage, Spike_PDB FROM covar WHERE WHO_Label=?
                ''',sql_label).fetchone()
                
                st.text(f"{label} Spike Protein:")
                components.html('''
                <script src="https://3Dmol.org/build/3Dmol-min.js"></script>     
                <script src="https://3Dmol.org/build/3Dmol.ui-min.js"></script>     

                <div style="height: 400px; width: 400px; position: relative;" class='viewer_3Dmoljs' data-pdb={} data-style1='cartoon:color=spectrum' data-backgroundcolor='0xffffff' data-style='stick' data-spin='axis:y;speed:1'></div>       
                '''.format(pdb_id), width=500 ,height=500 )

            #mutation_chart svg
            mutation_chart_location = f"resources/{chart_id}.svg"
            def render_svg(svg):
                #Renders the given svg string."""
                b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
                html = r'<img src="data:image/svg+xml;base64,%s"/>' % b64
                st.write(html, unsafe_allow_html=True)

            f = open(mutation_chart_location,"r")
            lines = f.readlines()
            line_string=''.join(lines)

            st.caption(f"Mutation chart of the {label} genome:")
            render_svg(line_string)
            
            st.markdown("---")
            subcol1, subcol2, subcol3 = st.columns(3)
            with subcol2:
                st.subheader("Epidemilogical_Info")

            #countries
            (v1, v2, v3, v4, v5, v6) = cur.execute('''
                    SELECT Value1, Value2, Value3, Value4, Value5, Other FROM covar WHERE WHO_Label=?
                    ''',sql_label).fetchone()
            (c1, c2, c3, c4, c5) =  cur.execute('''
                    SELECT Country1, Country2, Country3, Country4, Country5 FROM covar WHERE WHO_Label=?
                    ''',sql_label).fetchone()  
            c6 = "Other"  

            country_info = pd.DataFrame(
                                    {'Country': [c1, c2, c3, c4, c5, c6],
                                    'Percentage': [v1, v2, v3, v4, v5, v6]}
                                       )   
            
            epicol1, epicol2 = st.columns(2)
            with epicol1:
                st.dataframe(country_info)

            with epicol2:    
                with st.container():
                    plost.donut_chart(country_info, "Country","Percentage"
                                     ,legend="right", use_container_width=True)
            subepicol1, subepicol2, subepicol3 = st.columns([1,2,1])
            with subepicol2:
                st.caption("Percentage of cases in top 5 countries with the most cases")  

            con.close()

#about page
elif selected == "About":
    st.markdown("---")
    dbcol1, dbcol2, dbcol3 = st.columns([1,3,1])
    with dbcol2:
        url = "https://assets5.lottiefiles.com/private_files/lf30_mvurfbs7.json"
        about_json = load_lottieurl(url)
        st_lottie(about_json)
    
    st.info('''
    Credits
    - CoVar: A molecular and epidemilogical database for major SARS-CoV-2 variants
    - Developed by [Sina Farazmandi](mailto:s.farazmandi@modares.ac.ir) from Tarbiat Modares University, Tehran, Iran
    ''')
    st.warning('''
    Data sources
    - Epidemilogical data from [Cov-lineages.org](https://cov-lineages.org/)
    - Sample sequences from [NCBI SRA](https://www.ncbi.nlm.nih.gov/sra)
    - Reference sequence: hCoV-19/Wuhan/WIV04/2019 (WIV04)
    ''')
    st.error('''
    ⚠ Disclaimer 
    - This app has been developed for educational purposes as a project for Biological Databases course.
    - There's no guarantee that it will be maintained and the epidemilogical data stays relevant and up to date, hence YOU SHOUD ALWAYS DOUBLECHECK before using the data from this database in any kind of research.
    ''')
    st.success('''
    - For updated info about WHO monitoring status for variants, please visit [this page](https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/) from WHO.
    ''')

#help page
elif selected == "Help":
    st.markdown("---")
    dbcol1, dbcol2 = st.columns(2)
    with dbcol1:
        url = "https://assets5.lottiefiles.com/packages/lf20_ebj4mazi.json"
        help_json_1 = load_lottieurl(url)
        st_lottie(help_json_1)         
    with dbcol2:
        url = "https://assets5.lottiefiles.com/packages/lf20_mp9y8bjn.json"
        help_json_2 = load_lottieurl(url)
        st_lottie(help_json_2)  

    with st.expander("SARS-CoV-2 biology, evolution and mutations and what benefits could studying it have:"):
        st.video("resources/evolution.webm")
        vidcol1, vidcol2, vidcol3 = st.columns([5,3,3])
        with vidcol2:
            st.caption("[Source](https://www.youtube.com/watch?v=JmJIF47_f1s)")

    with st.expander("Pango lineages tree map:"):
        st.image("resources/pango.png")

    with st.expander("How to use?"):
        st.info('''
        It's really simple and straightforward! Here's the general guide:
        - Click on DB from above menu to go to the database page.
        - You can search variants either by Pango lineage or the label given by WHO.
        - Doesn't matter if the input is lower or uppercase.
        - Once you enter the input the page will get you the desired variant information.
        ''') 
