import streamlit as st
import pandas as pd
from sidefunctions import coddir,georreferenciacion

@st.cache(allow_output_mutation=True)
def getcatastro(direccion):
    try:    fcoddir = coddir(direccion)
    except: fcoddir = '' 
    #data         = pd.read_pickle(r'D:\Dropbox\Empresa\Buydepa\COLOMBIA\DESARROLLO\proyecto_market_analisis\data\data_catastro_completo_conjunto')
    data         = pd.read_pickle('data/data_catastro_completo_conjunto')
    datacatastro = pd.DataFrame()
    if fcoddir!='' and data.empty is False:
        datacatastro = data[data['coddir']==fcoddir]
    if datacatastro.empty:
        r = georreferenciacion({'direccion':direccion})
        if 'latitud' in r and 'longitud' in r:
            datacatastro = pd.DataFrame([{'latitud':r['latitud'],'longitud':r['longitud']}])
    return datacatastro