import streamlit as st
import xml.etree.ElementTree as ET
from collections import Counter

st.set_page_config(page_title="XML Property Report", layout="wide")
st.title("XML Property Report Tool")

uploaded_file = st.file_uploader("Upload your XML file", type=["xml"])

if uploaded_file:
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        properties = root.findall(".//property")

        st.header("Report")

        # === (a) Blank Phone Numbers from top-level <agents> ===
        st.subheader("a) Blank Phone Numbers")
        global_agents = root.find("agents")
        blank_phones = []

        if global_agents is not None:
            for agent in global_agents.findall("agent"):
                telephone = agent.findtext("telephone")
                if not telephone or telephone.strip() == "":
                    name = agent.findtext("name", "[No Name]")
                    email = agent.findtext("email", "[No Email]")
                    blank_phones.append((name, email))

            st.write(f"Number of agents with blank phone numbers: {len(blank_phones)}")
            if blank_phones:
                for name, email in blank_phones:
                    st.write(f"- Name: {name}, Email: {email}")
            else:
                st.success("No agents with blank phone numbers found.")
        else:
            st.warning("No global <agents> section found.")

        # === Properties section ===
        properties = root.findall(".//property")

        # (b) Unique and Duplicated External References
        st.subheader("b) External References")
        ext_refs = [p.findtext("external_reference") for p in properties]
        ext_ref_counts = Counter(ext_refs)
        unique_refs = sum(1 for count in ext_ref_counts.values() if count == 1)
        dup_refs = {ref: count for ref, count in ext_ref_counts.items() if count > 1}
        st.write("Unique External References:", unique_refs)
        st.write("Duplicated References Count:", len(dup_refs))
        st.write("Duplicated References:", list(dup_refs.keys()))

        # (c) Sales Status Count
        st.subheader("c) Sales Status Count")
        status_labels = {
            "1": "Available", "2": "Under Offer", "3": "Sold",
            "4": "Withdrawn", "5": "Let", "6": "Unconfirmed"
        }
        status_counts = Counter(p.findtext("sales_status") for p in properties)
        for code, label in status_labels.items():
            st.write(f"{label}: {status_counts.get(code, 0)}")

        # (d) Property Type Count
        st.subheader("d) Property Type Count")
        type_labels = {
            "1": "Offices", "2": "Industrial", "3": "Land",
            "4": "Retail", "5": "Leisure", "6": "Other"
        }
        type_counts = Counter(p.findtext("property_type") for p in properties)
        for code, label in type_labels.items():
            st.write(f"{label}: {type_counts.get(code, 0)}")

        # (e) Property Subtype Count
        st.subheader("e) Property Subtype Count")
        subtype_count = sum(1 for p in properties if p.findtext("property_subtype"))
        st.write("Properties with a subtype:", subtype_count)

        # (f) Unique Type + Subtype combinations
        st.subheader("f) Unique Property Type + Subtype")
        combos = set()
        for p in properties:
            t = p.findtext("property_type", "")
            s = p.findtext("property_subtype", "")
            combos.add((t, s))
        st.write("Unique combinations:", len(combos))

        # (g) Leasehold/To Let Error
        st.subheader("g) Leasehold/To Let Error")
        lease_errors = []
        for p in properties:
            ref = p.findtext("external_reference")
            for basis in p.findall(".//sale_basis"):
                tenure = basis.findtext("tenure_type")
                sale_type = basis.findtext("sale_type")
                if tenure in {"1", "2"} and sale_type == "2":
                    lease_errors.append(ref)
        st.write("Properties with Leasehold/To Let error:", lease_errors)

        # (h) For Sale/Price Type Error
        st.subheader("h) For Sale/Price Type Error")
        sale_errors = []
        for p in properties:
            ref = p.findtext("external_reference")
            for basis in p.findall(".//sale_basis"):
                if (
                    basis.findtext("sale_type") == "1"
                    and basis.findtext("tenure_type") == "3"
                    and basis.findtext("guide_price_type") != "3"
                ):
                    sale_errors.append(ref)
        st.write("Properties with For Sale/Price Type error:", sale_errors)

        # (i) Properties Missing Images
        st.subheader("i) Properties Missing Images")
        no_images = [p.findtext("external_reference") for p in properties if p.find("images") is None]
        st.write(f"Missing images: {len(no_images)}")
        st.write(no_images)

        # (j) Properties Missing Brochures
        st.subheader("j) Properties Missing Brochures")
        no_docs = [p.findtext("external_reference") for p in properties if p.find("documents") is None]
        st.write(f"Missing brochures: {len(no_docs)}")
        st.write(no_docs)

        # (k) Duplicate Address Lines
        st.subheader("k) Duplicate Address Lines")
        dup_address = []
        for p in properties:
            ref = p.findtext("external_reference")
            name = p.findtext("name", "")
            address_fields = [p.findtext(f"address/{tag}", "") for tag in [
                "address1", "address2", "address3", "town_city", "county", "postcode"
            ]]
            address_values = [v for v in [name] + address_fields if v]
            if len(address_values) != len(set(address_values)):
                dup_address.append((ref, name, *address_fields))
        st.write("Properties with duplicate address fields:")
        for entry in dup_address:
            st.write(entry)

        # (l) LAT/LONG missing (only where tags exist but are blank)
        st.subheader("l) LAT/LONG Missing")
        latlong_missing = []
        for p in properties:
            lat_elem = p.find("latitude")
            lon_elem = p.find("longitude")
            if lat_elem is not None and lon_elem is not None:
                lat_text = lat_elem.text.strip() if lat_elem.text else ""
                lon_text = lon_elem.text.strip() if lon_elem.text else ""
                if not lat_text or not lon_text:
                    latlong_missing.append(p.findtext("external_reference"))

        st.write(f"Properties where <latitude> and/or <longitude> exist but are blank: {len(latlong_missing)}")
        if latlong_missing:
            st.write(latlong_missing)
        else:
            st.success("No LAT/LONG fields are blank when tags are present.")

        # (m) Size Missing or Invalid
        st.subheader("m) Size Missing or Invalid")
        invalid_sizes = []
        for p in properties:
            ref = p.findtext("external_reference")
            try:
                size_from = float(p.findtext("size/size_from", ""))
                size_to = float(p.findtext("size/size_to", ""))
            except:
                invalid_sizes.append(ref)
        st.write("Invalid or missing sizes:", invalid_sizes)

        # (n) Postcode Blank
        st.subheader("n) Postcode Blank")
        blank_postcodes = [p.findtext("external_reference") for p in properties if not p.findtext("address/postcode")]
        st.write("Properties with blank postcode:", blank_postcodes)

    except Exception as e:
        st.error(f"An error occurred while processing the XML file: {e}")

import pandas as pd

st.header("External Ref Comparison")

xls_file = st.file_uploader("Upload Excel file for comparison", type=["xls", "xlsx"])

if xls_file:
    try:
        # Load Excel
        df_xls = pd.read_excel(xls_file)
        xls_refs = df_xls['Property ref'].astype(str).str.strip()
        xml_refs = [p.findtext("external_reference", "").strip() for p in properties]

        # Count XML refs
        xml_ref_counts = Counter(xml_refs)

        # === (A) Excel 'property ref' not found in XML or found more than once ===
        missing_or_duplicated_in_xml = []
        for _, row in df_xls.iterrows():
            ref = str(row['Property ref']).strip()
            if xml_ref_counts.get(ref, 0) != 1:
                entry = {
                    'Property url': row.get('Property url', ''),
                    'Property ref': ref,
                    'Sale status': row.get('Sale status', ''),
                    'Date created': row.get('Date created', ''),
                    'Date last edited': row.get('Date last edited', '')
                }
                missing_or_duplicated_in_xml.append(entry)

        st.subheader("Excel refs not found or duplicated in XML")
        if missing_or_duplicated_in_xml:
            df_result = pd.DataFrame(missing_or_duplicated_in_xml)
            st.dataframe(df_result)
        else:
            st.success("All Excel 'Property ref' values matched exactly once in XML.")

        # === (B) XML <external_reference> not found in Excel ===
        st.subheader("XML refs missing in Excel")
        xls_set = set(xls_refs)
        xml_only = []

        status_map = {
            "1": "Available", "2": "Under Offer", "3": "Sold",
            "4": "Withdrawn", "5": "Let", "6": "Unconfirmed"
        }

        for p in properties:
            ref = p.findtext("external_reference", "").strip()
            if ref not in xls_set:
                sales_status = p.findtext("sales_status", "").strip()
                xml_only.append({
                    'External Reference': ref,
                    'Sales Status': status_map.get(sales_status, "Unknown")
                })

        if xml_only:
            st.dataframe(pd.DataFrame(xml_only))
        else:
            st.success("All XML references are present in the Excel file.")

    except Exception as e:
        st.error(f"An error occurred during Excel comparison: {e}")

import io

def truncate(value, limit=30000):
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "… [TRUNCATED]"
    return value

st.header("Convert XML ➜ Excel")

if st.button("Convert now"):
    try:
        # Lookup dictionaries ------------------------------------------------
        ptype_map = {"1":"Offices","2":"Industrial","3":"Land","4":"Retail","5":"Leisure","6":"Other"}
        loc_acc_map = {"0":"Unknown","1":"Low","2":"Medium","3":"High","4":"Exact"}
        size_type_map = {"1":"Sq Mt","2":"Sq Ft","3":"Acres","4":"Hectare"}
        tenure_map = {"1":"Freehold","2":"Leasehold","3":"NA"}
        sale_type_map = {"1":"For Sale","2":"To Let"}
        gp_type_map = {"1":"Per Sq Ft","2":"Per Annum","3":"NA","4":"Per Sq M","5":"Per Hectare","6":"Per Acre","7":"Per Month"}
        status_map = {"1":"Available","2":"Under Offer","3":"Sold","4":"Withdrawn","5":"Let","6":"Unconfirmed"}
        force_map = {"1":"YES","0":"NO"}
        desc_map = {"1":"General","2":"Location","3":"Accommodation","4":"Terms","5":"Specification"}
        img_type_map = {"1":"Photo","2":"Artist Impression","3":"Floorplan","4":"Site Plan"}
        doc_type_map = {"1":"PDF","2":"Word","4":"Excel"}
        link_type_map = {"1":"Virtual Tour","2":"3d Tour","3":"Video","4":"Website"}
        prop_subtype_map = {
            ("1", "57"): "Offices", ("1", "58"): "Business Park", ("1", "59"): "Serviced Office",
            ("1", "60"): "Science Park", ("1", "61"): "Healthcare - Surgeries", ("1", "84"): "Traditional",
            ("1", "85"): "Modern", ("1", "86"): "Refurbished", ("1", "87"): "Grade A", ("1", "88"): "Grade B",
            ("1", "113"): "Design & Build", ("1", "115"): "Research & Development", ("1", "119"): "Investment",
            ("1", "125"): "Mixed Use", ("1", "126"): "Non residential Institution", ("1", "137"): "Land/Development",
            ("1", "139"): "Class E - incl Retail Leisure Healthcare", ("1", "140"): "Or Retail Use",
            ("1", "141"): "With industrial", ("2", "62"): "General Industrial", ("2", "63"): "Light Industrial",
            ("2", "64"): "Warehouse / Distribution", ("2", "65"): "Industrial Park", ("2", "66"): "Trade Park",
            ("2", "67"): "Non Food Retail Warehouse", ("2", "68"): "Self Storage",
            ("2", "69"): "Motor Trade - showroom/vehicle repair", ("2", "89"): "Bonded Warehouse",
            ("2", "90"): "Warehouse", ("2", "91"): "Business Unit", ("2", "92"): "High Tech Unit",
            ("2", "93"): "Food Production", ("2", "94"): "Lab Space", ("2", "95"): "Managed Workshop",
            ("2", "96"): "Manufacturing/Production", ("2", "97"): "Workshop Studio", ("2", "98"): "Distribution",
            ("2", "99"): "Yard Area", ("2", "100"): "Other Industrial", ("2", "112"): "Design & Build",
            ("2", "116"): "Research & Development", ("2", "118"): "Investment", ("2", "124"): "Data Centres",
            ("2", "127"): "Land/Development", ("2", "128"): "Mixed Use", ("2", "142"): "Trade Counter",
            ("2", "143"): "Class E - incl Office Retail Leisure Healthcare", ("2", "151"): "Open Storage",
            ("3", "101"): "Mixed Use", ("3", "102"): "Agricultural", ("3", "103"): "Serviced",
            ("3", "104"): "Sub-Serviced", ("3", "105"): "Residential", ("3", "106"): "Science Park",
            ("3", "107"): "Vacant Site", ("3", "108"): "Business Park",
            ("3", "109"): "Industrial Scottish Planning use 4", ("3", "110"): "Industrial Scottish Planning use 5",
            ("3", "111"): "Industrial Scottish Planning use 6", ("3", "114"): "Design & Build",
            ("3", "117"): "Farm", ("3", "122"): "Investment", ("3", "129"): "Non residential Institution",
            ("3", "130"): "Residential Institution", ("3", "152"): "Open Storage", ("3", "153"): "Development",
            ("3", "n/a"): "exc field from xml", ("4", "70"): "General Retail", ("4", "71"): "Retail - High Street",
            ("4", "72"): "Retail - out of town", ("4", "73"): "Shopping Centre unit",
            ("4", "74"): "Motor Trade - filling station", ("4", "75"): "Retail Park",
            ("4", "120"): "Investment", ("4", "131"): "Mixed Use", ("4", "132"): "Motor Trade - showroom",
            ("4", "144"): "Class E - incl Office Leisure Healthcare", ("4", "145"): "Or Office Use",
            ("4", "146"): "Business for sale", ("4", "154"): "Land/Development", ("5", "76"): "Hotel",
            ("5", "77"): "General Leisure", ("5", "78"): "Restaurants / Cafes", ("5", "79"): "Pubs/Bars/Clubs",
            ("5", "121"): "Investment", ("5", "133"): "Leisure Park", ("5", "134"): "Mixed Use",
            ("5", "147"): "Class E - incl Office Retail Healthcare", ("5", "148"): "Business for sale",
            ("5", "155"): "Land/Development", ("6", "80"): "Residential", ("6", "81"): "Residential Institution",
            ("6", "82"): "Non residential Institution", ("6", "83"): "Healthcare - hospitals",
            ("6", "123"): "Investment", ("6", "135"): "Healthcare - Consulting Rooms/Medical Offices",
            ("6", "136"): "Mixed Use", ("6", "138"): "Healthcare - General", ("6", "149"): "Business for sale",
            ("6", "150"): "Class E - incl Office Retail Leisure Healthcare", ("6", "156"): "Land/Development"
        }

        rows = []
        for p in properties:
            d = {}
            # Basic id -------------------------------------------------------
            d['external_reference'] = p.findtext('external_reference','')
            d['action']            = p.findtext('action','')
            d['name']              = p.findtext('name','')

            # Address -------------------------------------------------------
            for tag in ['address1','address2','address3','town_city','county','postcode','country']:
                d[tag] = p.findtext(f'address/{tag}','')

            # Location ------------------------------------------------------
            loc = p.find('location')
            if loc is not None:
                d['location_accuracy'] = loc_acc_map.get(loc.attrib.get('accuracy',''),'')
                d['latitude']  = loc.findtext('latitude','')
                d['longitude'] = loc.findtext('longitude','')
            else:
                d['location_accuracy']=d['latitude']=d['longitude']=''

            # Property meta --------------------------------------------------
            ptype = p.findtext('property_type','').strip()
            psub  = p.findtext('property_subtype','').strip()
            
            d['property_type']    = ptype_map.get(ptype, '')
            d['property_subtype'] = prop_subtype_map.get((ptype, psub), psub)
            d['sales_status']     = status_map.get(p.findtext('sales_status',''),'')

            # Main‑agent email ----------------------------------------------
            d['email'] = ''
            for ag in p.findall('.//agents/agent'):
                if ag.findtext('main_agent')=='1':
                    d['email']=ag.findtext('email','');break

            # Size -----------------------------------------------------------
            stype = (p.find('size') or {}).get('type','') if isinstance(p.find('size'), ET.Element) else ''
            d['size type'] = size_type_map.get(stype,'')
            d['size_from'] = p.findtext('size/size_from','')
            d['size_to']   = p.findtext('size/size_to','')

            # Up to TWO sale_basis blocks ------------------------------------
            bases = p.findall('sale_basises/sale_basis') or p.findall('sale_basis')
            for i in range(2):
                suffix = f" {i+1}"
                if i < len(bases):
                    sb = bases[i]
                    d[f'tenure type{suffix}']       = tenure_map.get(sb.findtext('tenure_type',''),'')
                    d[f'sale type{suffix}']         = sale_type_map.get(sb.findtext('sale_type',''),'')
                    d[f'guide price{suffix}']       = sb.findtext('guide_price','')
                    d[f'guide price type{suffix}']  = gp_type_map.get(sb.findtext('guide_price_type',''),'')
                else:
                    for col in ['tenure type','sale type','guide price','guide price type']:
                        d[f'{col}{suffix}']=''

            # Descriptions ---------------------------------------------------
            for de in p.findall('descriptions/description'):
                label = desc_map.get(de.get('type'))
                if label:
                    d[label] = (de.text or '').strip()

            # Images ---------------------------------------------------------
            imgs = p.findall('images/image')
            d['image caption'] = ', '.join(i.findtext('caption','') for i in imgs)
            d['image_type']    = ', '.join(img_type_map.get(i.findtext('type',''),'') for i in imgs)
            d['image']         = ', '.join(truncate(i.findtext('url') or i.findtext('absolute_path') or i.findtext('data','')) for i in imgs)

            # Documents ------------------------------------------------------
            docs = p.findall('documents/document')
            d['document description'] = ', '.join(doc.findtext('description','') for doc in docs)
            d['document type']        = ', '.join(doc_type_map.get(doc.findtext('type',''),'') for doc in docs)
            d['show_on_site']         = ', '.join(doc.findtext('show_on_site','') for doc in docs)
            d['brochure']             = ', '.join(truncate(doc.findtext('url') or doc.findtext('absolute_path') or doc.findtext('data','')) for doc in docs)

            # Links ----------------------------------------------------------
            links = p.findall('links/link')
            d['link name']  = ', '.join(l.findtext('name','') for l in links)
            d['link type']  = ', '.join(link_type_map.get(l.findtext('type',''),'') for l in links)
            d['url']        = ', '.join(truncate(l.findtext('url','')) for l in links)
            d['width']      = ', '.join(l.findtext('width','') for l in links)
            d['height']     = ', '.join(l.findtext('height','') for l in links)

            # Last‑updated & force_update ------------------------------------
            d['last_updated'] = p.findtext('last_updated','')
            d['force_update'] = force_map.get(p.findtext('force_update',''),'')

            rows.append(d)

        df = pd.DataFrame(rows)
        out = io.BytesIO()
        with pd.ExcelWriter(
                out,
                engine="xlsxwriter",
                engine_kwargs={"options": {"strings_to_urls": False}}
            ) as xw:
            df.to_excel(xw, index=False, sheet_name="Properties")

        st.download_button(
            "⬇️ Download Excel", out.getvalue(), file_name="xml_properties.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success(f"Excel generated with {len(df)} rows, including all requested fields.")

    except Exception as e:
        st.error(f"❌ Export failed: {e}")
