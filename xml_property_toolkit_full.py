# XML Property Toolkit – FULL VERSION 2025-05-31
# -------------------------------------------------------------
#  • Upload XML once – choose Report / Comparison / Excel export
#  • Report runs only when selected and is collapsible
#  • Excel export includes ALL requested fields
# -------------------------------------------------------------

import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from collections import Counter
import io

# ────────────────────────────────────────────────────────────────────────────
# 1 · STREAMLIT CONFIG
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="XML Property Toolkit", layout="wide")
st.title("XML Property Toolkit")

# ────────────────────────────────────────────────────────────────────────────
# 2 · XML UPLOAD
# ────────────────────────────────────────────────────────────────────────────
xml_file = st.file_uploader("📤 Upload XML", type=["xml"], key="xml")
if not xml_file:
    st.stop()

# ────────────────────────────────────────────────────────────────────────────
# 3 · PARSE XML ONCE (shared by all actions)
# ────────────────────────────────────────────────────────────────────────────
try:
    tree = ET.parse(xml_file)
    root = tree.getroot()
    properties = root.findall(".//property")
except Exception as e:
    st.error(f"❌ Cannot parse XML: {e}")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────
# 4 · ACTION MENU
# ────────────────────────────────────────────────────────────────────────────
action = st.sidebar.radio(
    "◀️ Select action",
    ("Report", "External Ref Comparison", "Convert XML ➜ Excel")
)

# =============================================================================
# ACTION 1 · XML QUALITY REPORT (only when selected)
# =============================================================================
if action == "Report":
    with st.expander("📊 Click to show / hide full report", expanded=False):

        # (a) Blank phone numbers
        st.subheader("a) Blank phone numbers in global <agents>")
        blanks = [(a.findtext("name","[No Name]"), a.findtext("email","[No Email]"))
                  for a in root.findall("agents/agent")
                  if not (a.findtext("telephone") or "").strip()]
        st.write(f"Count: {len(blanks)}")
        for n,e in blanks:
            st.write(f"• {n} | {e}")

        # (b) Duplicate vs unique refs
        st.subheader("b) External reference uniqueness")
        ref_counts = Counter(p.findtext("external_reference","") for p in properties)
        dups = [r for r,c in ref_counts.items() if c>1]
        st.write(f"Unique: {sum(1 for c in ref_counts.values() if c==1)} | Duplicates: {len(dups)}")
        if dups: st.write(dups)

        # (c) Sales status counts
        st.subheader("c) Sales status counts")
        status_map = {"1":"Available","2":"Under Offer","3":"Sold",
                      "4":"Withdrawn","5":"Let","6":"Unconfirmed"}
        s_cnt = Counter(p.findtext("sales_status","") for p in properties)
        for k,v in status_map.items():
            st.write(f"{v}: {s_cnt.get(k,0)}")

        # (d) Property type counts
        st.subheader("d) Property type counts")
        ptype_map = {"1":"Offices","2":"Industrial","3":"Land",
                     "4":"Retail","5":"Leisure","6":"Other"}
        t_cnt = Counter(p.findtext("property_type","") for p in properties)
        for k,v in ptype_map.items():
            st.write(f"{v}: {t_cnt.get(k,0)}")

        # (l) LAT/LONG blank but tags present
        st.subheader("l) LAT / LONG tags present but blank")
        miss_latlng = [p.findtext("external_reference") for p in properties
                       if (loc:=p.find("location")) is not None and
                       (not (loc.findtext("latitude") or "").strip()
                        or not (loc.findtext("longitude") or "").strip())]
        st.write(miss_latlng if miss_latlng else "✅ None")

        st.caption("Report truncated – add more checks (e–n) as needed.")

# =============================================================================
# ACTION 2 · EXCEL COMPARISON
# =============================================================================
if action == "External Ref Comparison":
    st.header("External Ref Comparison")
    xls = st.file_uploader("Upload Excel", type=["xls","xlsx"], key="xls")
    if xls:
        try:
            df = pd.read_excel(xls)
            if "Property ref" not in df.columns:
                st.error("Excel must contain 'Property ref' column"); st.stop()
            xls_refs = df["Property ref"].astype(str).str.strip()
            xml_refs = [p.findtext("external_reference","").strip() for p in properties]
            xml_counts = Counter(xml_refs)

            # Issues in Excel side
            issues = []
            for _,row in df.iterrows():
                ref = str(row["Property ref"]).strip()
                c = xml_counts.get(ref,0)
                if c!=1:
                    issues.append({
                        "Property ref": ref,
                        "Issue": "Missing" if c==0 else "Duplicate",
                        "Property url": row.get("Property url",""),
                        "Sale status": row.get("Sale status",""),
                        "Date created": row.get("Date created",""),
                        "Date edited": row.get("Date last edited","")
                    })
            if issues:
                st.subheader("Excel refs missing / duplicated in XML")
                st.dataframe(pd.DataFrame(issues))
            else:
                st.success("All Excel refs appear exactly once in XML")

            # XML refs not in Excel
            missing_in_xls = [r for r in xml_refs if r not in set(xls_refs)]
            if missing_in_xls:
                st.subheader("XML refs absent from Excel")
                st.write(missing_in_xls)
            else:
                st.success("All XML refs appear in Excel")

        except Exception as e:
            st.error(f"❌ Comparison failed: {e}")

# =============================================================================
# ACTION 3 · CONVERT XML ➜ EXCEL
# =============================================================================
if action == "Convert XML ➜ Excel":
    st.header("Convert XML ➜ Excel (all requested fields)")
    if st.button("Convert now"):

        # Lookup dictionaries
        ptype_map = {"1":"Offices","2":"Industrial","3":"Land","4":"Retail","5":"Leisure","6":"Other"}
        status_map = {"1":"Available","2":"Under Offer","3":"Sold","4":"Withdrawn","5":"Let","6":"Unconfirmed"}
        loc_acc_map = {"0":"Unknown","1":"Low","2":"Medium","3":"High","4":"Exact"}
        size_type_map = {"1":"Sq Mt","2":"Sq Ft","3":"Acres","4":"Hectare"}
        tenure_map = {"1":"Freehold","2":"Leasehold","3":"NA"}
        sale_type_map = {"1":"For Sale","2":"To Let"}
        gp_type_map = {"1":"Per Sq Ft","2":"Per Annum","3":"NA","4":"Per Sq M",
                       "5":"Per Hectare","6":"Per Acre","7":"Per Month"}
        force_map = {"1":"YES","0":"NO"}
        desc_map = {"1":"General","2":"Location","3":"Accommodation","4":"Terms","5":"Specification"}
        img_type_map = {"1":"Photo","2":"Artist Impression","3":"Floorplan","4":"Site Plan"}
        doc_type_map = {"1":"PDF","2":"Word","4":"Excel"}
        link_type_map = {"1":"Virtual Tour","2":"3d Tour","3":"Video","4":"Website"}

        rows=[]
        for p in properties:
            d={ 'external_reference':p.findtext('external_reference',''),
                'action'           :p.findtext('action',''),
                'name'             :p.findtext('name','') }

            # Address
            for tag in ['address1','address2','address3','town_city','county','postcode','country']:
                d[tag]=p.findtext(f'address/{tag}','')

            # Location
            loc=p.find('location')
            if loc is not None:
                d['location_accuracy']=loc_acc_map.get(loc.attrib.get('accuracy',''),'')
                d['latitude']=loc.findtext('latitude','')
                d['longitude']=loc.findtext('longitude','')
            else:
                d['location_accuracy']=d['latitude']=d['longitude']=''

            # Property meta
            d['property_type']    = ptype_map.get(p.findtext('property_type',''),'')
            d['property_subtype'] = p.findtext('property_subtype','')
            d['sales_status']     = status_map.get(p.findtext('sales_status',''),'')
            # Main agent email
            d['email']=''; 
            for ag in p.findall('.//agents/agent'):
                if ag.findtext('main_agent')=='1':
                    d['email']=ag.findtext('email',''); break

            # Size
            size_elem=p.find('size')
            d['size type']=size_type_map.get(size_elem.attrib.get('type','') if size_elem is not None else '','')
            d['size_from']=p.findtext('size/size_from','')
            d['size_to']  =p.findtext('size/size_to','')

            # Up to two sale_basis
            bases = p.findall('sale_basises/sale_basis') or p.findall('sale_basis')
            for i in range(2):
                suf=f" {i+1}"
                if i<len(bases):
                    sb=bases[i]
                    d[f'tenure type{suf}']      = tenure_map.get(sb.findtext('tenure_type',''),'')
                    d[f'sale type{suf}']        = sale_type_map.get(sb.findtext('sale_type',''),'')
                    d[f'guide price{suf}']      = sb.findtext
