import streamlit as st
from openai import OpenAI
import base64
import json
import os
import re
import copy

st.set_page_config(page_title="Grok Writing Studio", layout="wide")
st.title("✍️ Grok Writing Studio")
st.caption("Your full AI-powered book writing studio — projects 100% isolated")

os.makedirs("projects", exist_ok=True)

# ====================== PRICING ======================
MODEL_PRICING = {
    "grok-4.20-reasoning": {"input": 2.00, "output": 6.00},
    "grok-4-1-fast-reasoning": {"input": 0.20, "output": 0.50},
    "grok-4.20-non-reasoning": {"input": 2.00, "output": 6.00},
}

def get_default_data(name="Project", desc="", genre=""):
    return {
        "project_name": name,
        "project_description": desc,
        "genre": genre,
        "style_reference": "",
        "chapters": [{"title": "Chapter 1", "content": ""}],
        "characters": [], "places": [], "plot": [], "storyline": [], "outline": []
    }

def save_project(name, data):
    path = f"projects/{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_project(name):
    path = f"projects/{name}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return copy.deepcopy(json.load(f))
    return None

def word_count(text):
    return len(re.findall(r'\b\w+\b', text)) if text else 0

# ====================== SESSION CREDIT TRACKER ======================
if "session_cost" not in st.session_state:
    st.session_state.session_cost = 0.0
if "last_call_cost" not in st.session_state:
    st.session_state.last_call_cost = 0.0

def estimate_cost(prompt_tokens, completion_tokens, model):
    pricing = MODEL_PRICING.get(model, {"input": 2.0, "output": 6.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    total = input_cost + output_cost
    st.session_state.last_call_cost = round(total, 4)
    st.session_state.session_cost = round(st.session_state.session_cost + total, 4)
    return total

# ====================== FORCE FRESH LOAD ======================
if "current_project" not in st.session_state:
    st.session_state.current_project = "Project"

if "last_loaded" not in st.session_state or st.session_state.last_loaded != st.session_state.current_project:
    fresh = load_project(st.session_state.current_project)
    if fresh is None:
        fresh = get_default_data()
        save_project(st.session_state.current_project, fresh)
    st.session_state.data = fresh
    st.session_state.last_loaded = st.session_state.current_project

data = st.session_state.data

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("📁 My Projects")
    project_files = sorted([f[:-5] for f in os.listdir("projects") if f.endswith(".json")])
    
    for proj in project_files:
        if st.button(f"📄 {proj}", key=f"select_{proj}", use_container_width=True):
            if proj != st.session_state.current_project:
                st.session_state.current_project = proj
                st.rerun()
    
    st.divider()
    if st.button("➕ Add New Project", use_container_width=True):
        st.session_state.show_add_form = True
    if st.button("🗑️ Delete Current Project", use_container_width=True):
        st.session_state.show_delete_confirm = True

    st.divider()
    st.header("🔑 API Settings")
    st.session_state.api_key = st.text_input("xAI API Key", value=st.session_state.get("api_key", ""), type="password")
    model = st.selectbox("Model", list(MODEL_PRICING.keys()), index=1)  # Default to fast model

    st.divider()
    st.header("💰 Credit Usage (Session)")
    st.write(f"**Last AI call:** ${st.session_state.last_call_cost:.4f}")
    st.write(f"**Session total:** ${st.session_state.session_cost:.4f}")
    if st.button("Reset Session Cost"):
        st.session_state.session_cost = 0.0
        st.session_state.last_call_cost = 0.0
        st.rerun()

    st.divider()
    st.header("💾 Project Backup")
    col_dl, col_ul = st.columns(2)
    with col_dl:
        if st.button("💾 Download Current Project"):
            st.download_button(
                label="Download JSON",
                data=json.dumps(data, indent=2),
                file_name=f"{data.get('project_name', 'project')}.json",
                mime="application/json"
            )
    with col_ul:
        uploaded = st.file_uploader("📤 Upload Project", type="json", key="upload_project")
        if uploaded:
            try:
                uploaded_data = json.loads(uploaded.getvalue())
                st.session_state.data = uploaded_data
                st.session_state.current_project = uploaded_data.get("project_name", "Project")
                save_project(st.session_state.current_project, uploaded_data)
                st.success("✅ Project loaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load file: {e}")

# ====================== ADD / DELETE / EDIT PROJECT ======================
if st.session_state.get("show_add_form"):
    with st.form("add_project_form"):
        st.subheader("Create New Project")
        new_name = st.text_input("Project Name", "My New Book")
        new_desc = st.text_area("Description", height=100)
        new_genre = st.text_input("Genre")
        if st.form_submit_button("Create Project") and new_name.strip():
            name = new_name.strip()
            new_data = get_default_data(name, new_desc, new_genre)
            save_project(name, new_data)
            st.session_state.current_project = name
            st.success(f"✅ Created '{name}'")
            del st.session_state.show_add_form
            st.rerun()

if st.session_state.get("show_delete_confirm"):
    st.warning(f"Delete **{st.session_state.current_project}** permanently?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, delete"):
            path = f"projects/{st.session_state.current_project}.json"
            if os.path.exists(path):
                os.remove(path)
            st.session_state.current_project = "Project"
            del st.session_state.show_delete_confirm
            st.rerun()
    with col2:
        if st.button("Cancel"):
            del st.session_state.show_delete_confirm
            st.rerun()

col_title, col_edit = st.columns([5, 1])
with col_title:
    st.subheader(f"Current Project: **{data.get('project_name', 'Project')}**")
    if data.get("genre"): st.caption(f"Genre: {data.get('genre')}")
    if data.get("project_description"): st.caption(data.get("project_description"))

with col_edit:
    if st.button("✏️ Edit Project Info"):
        st.session_state.show_edit_form = True

if st.session_state.get("show_edit_form"):
    with st.form("edit_project_form"):
        st.subheader("Edit Project")
        edit_name = st.text_input("Project Name", data.get("project_name", ""))
        edit_desc = st.text_area("Description", data.get("project_description", ""), height=100)
        edit_genre = st.text_input("Genre", data.get("genre", ""))
        if st.form_submit_button("Save Changes"):
            new_name = edit_name.strip()
            if new_name and new_name != data.get("project_name"):
                old_path = f"projects/{data.get('project_name')}.json"
                new_path = f"projects/{new_name}.json"
                if os.path.exists(new_path):
                    st.error("A project with that name already exists.")
                else:
                    os.rename(old_path, new_path)
                    st.session_state.current_project = new_name
            data["project_name"] = new_name
            data["project_description"] = edit_desc
            data["genre"] = edit_genre
            save_project(st.session_state.current_project, data)
            st.success("✅ Saved")
            del st.session_state.show_edit_form
            st.rerun()

# ====================== CALL GROK WITH COST TRACKING ======================
def call_grok(prompt, image_bytes=None, temperature=0.7):
    if not st.session_state.get("api_key"):
        st.error("Please enter your xAI API Key")
        return "❌ No API key"
    
    client = OpenAI(base_url="https://api.x.ai/v1", api_key=st.session_state.api_key)
    
    messages = [{"role": "system", "content": "You are an expert creative writing assistant."}]
    content = [{"type": "text", "text": prompt}]
    if image_bytes:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
    messages.append({"role": "user", "content": content})
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=4000
        )
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        estimate_cost(prompt_tokens, completion_tokens, model)
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ====================== TABS ======================
tab1, tab2, tab3, tab4 = st.tabs(["📖 Manuscript", "🌍 World Building", "📋 Story Structure", "🤖 AI Tools"])

# TAB 1: MANUSCRIPT
with tab1:
    st.subheader("Manuscript")
    total_words = sum(word_count(ch["content"]) for ch in data["chapters"])
    st.info(f"**Total Manuscript Word Count: {total_words:,} words**")
    
    new_style = st.text_area("Writing Style Reference", value=data.get("style_reference", ""), height=120, key=f"style_ref_{st.session_state.current_project}")
    if new_style != data.get("style_reference"):
        data["style_reference"] = new_style
        save_project(st.session_state.current_project, data)

    for i, chapter in enumerate(data["chapters"]):
        chapter_words = word_count(chapter["content"])
        with st.expander(f"📄 {chapter['title']} — {chapter_words:,} words", expanded=i == 0):
            col1, col2 = st.columns([4, 1])
            with col1:
                chapter["title"] = st.text_input("Title", chapter["title"], key=f"ch_title_{i}_{st.session_state.current_project}")
                chapter["content"] = st.text_area("Content", chapter["content"], height=400, key=f"ch_content_{i}_{st.session_state.current_project}")
            with col2:
                if st.button("✨ Enhance", key=f"enh_{i}_{st.session_state.current_project}"):
                    style = f"Match this style: {data.get('style_reference', '')}" if data.get("style_reference") else ""
                    prompt = f"{style}\nImprove or continue this chapter:\n{chapter['content']}"
                    with st.spinner("Writing..."):
                        result = call_grok(prompt)
                        chapter["content"] += "\n\n" + result
                    save_project(st.session_state.current_project, data)
                    st.rerun()
                if st.button("🔍 Spelling & Grammar", key=f"spell_{i}_{st.session_state.current_project}"):
                    prompt = f"Fix spelling and grammar. Return only corrected text:\n{chapter['content']}"
                    with st.spinner("Checking..."):
                        chapter["content"] = call_grok(prompt, temperature=0)
                    save_project(st.session_state.current_project, data)
                    st.rerun()
                if st.button("💡 Feedback", key=f"fb_{i}_{st.session_state.current_project}"):
                    with st.spinner("Analyzing..."):
                        st.info(call_grok(f"Give creative feedback:\n{chapter['content']}"))
                uploaded = st.file_uploader("📸 Upload photo/screenshot", type=["png","jpg","jpeg"], key=f"img_{i}_{st.session_state.current_project}")
                if uploaded and st.button("Transcribe", key=f"ocr_{i}_{st.session_state.current_project}"):
                    with st.spinner("Reading..."):
                        text = call_grok("Transcribe all text accurately.", uploaded.getvalue())
                        chapter["content"] += "\n\n" + text
                    save_project(st.session_state.current_project, data)
                    st.rerun()
                if st.button("🗑️ Delete Chapter", key=f"delch_{i}_{st.session_state.current_project}"):
                    st.session_state["del_ch"] = i

    if "del_ch" in st.session_state:
        idx = st.session_state.del_ch
        st.warning(f"Delete **{data['chapters'][idx]['title']}**?")
        if st.button("Yes, delete"):
            del data["chapters"][idx]
            save_project(st.session_state.current_project, data)
            del st.session_state.del_ch
            st.rerun()
        if st.button("Cancel"):
            del st.session_state.del_ch
            st.rerun()

    if st.button("➕ Add New Chapter"):
        data["chapters"].append({"title": f"Chapter {len(data['chapters'])+1}", "content": ""})
        save_project(st.session_state.current_project, data)
        st.rerun()

# TAB 2: WORLD BUILDING
with tab2:
    st.subheader("👥 Characters")
    if st.button("➕ Add New Character"):
        data["characters"].append({"name": "New Character", "description": "", "image_base64": None})
        save_project(st.session_state.current_project, data)
        st.rerun()
    
    for idx, char in enumerate(data["characters"]):
        with st.expander(f"👤 {char.get('name', 'Unnamed')}", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                char["name"] = st.text_input("Name", char.get("name", ""), key=f"cname_{idx}_{st.session_state.current_project}")
                char["description"] = st.text_area("Description", char.get("description", ""), height=200, key=f"cdesc_{idx}_{st.session_state.current_project}")
            with col2:
                if char.get("image_base64"):
                    st.image(base64.b64decode(char["image_base64"]), width=140)
                uploaded = st.file_uploader("📸 Photo", type=["png","jpg","jpeg"], key=f"cimg_{idx}_{st.session_state.current_project}")
                if uploaded:
                    char["image_base64"] = base64.b64encode(uploaded.getvalue()).decode()
                    save_project(st.session_state.current_project, data)
                    st.success("Photo saved")
                    st.rerun()
                if st.button("🗑️ Delete Character", key=f"delc_{idx}_{st.session_state.current_project}"):
                    st.session_state["del_char"] = idx
    
    if "del_char" in st.session_state:
        idx = st.session_state.del_char
        st.warning(f"Delete character **{data['characters'][idx].get('name')}**?")
        if st.button("Yes, delete"):
            del data["characters"][idx]
            save_project(st.session_state.current_project, data)
            del st.session_state.del_char
            st.rerun()
        if st.button("Cancel"):
            del st.session_state.del_char
            st.rerun()
    
    if st.button("🔄 AI Update Characters from Manuscript"):
        full_text = "\n\n".join(ch["content"] for ch in data["chapters"])
        prompt = f"""Read the full manuscript and update every character with detailed attributes.
Check for inconsistencies.
Current characters: {json.dumps(data['characters'], indent=2) if data['characters'] else 'None'}
Manuscript: {full_text[:15000]}"""
        with st.spinner("Analyzing..."):
            result = call_grok(prompt, temperature=0.3)
        st.info(result)

    st.subheader("📍 Places")
    if st.button("➕ Add New Place"):
        data["places"].append({"name": "New Place", "description": "", "image_base64": None})
        save_project(st.session_state.current_project, data)
        st.rerun()
    
    for idx, place in enumerate(data["places"]):
        with st.expander(f"📍 {place.get('name', 'Unnamed')}", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                place["name"] = st.text_input("Name", place.get("name", ""), key=f"pname_{idx}_{st.session_state.current_project}")
                place["description"] = st.text_area("Description", place.get("description", ""), height=200, key=f"pdesc_{idx}_{st.session_state.current_project}")
            with col2:
                if place.get("image_base64"):
                    st.image(base64.b64decode(place["image_base64"]), width=140)
                uploaded = st.file_uploader("📸 Photo", type=["png","jpg","jpeg"], key=f"pimg_{idx}_{st.session_state.current_project}")
                if uploaded:
                    place["image_base64"] = base64.b64encode(uploaded.getvalue()).decode()
                    save_project(st.session_state.current_project, data)
                    st.success("Photo saved")
                    st.rerun()
                if st.button("🗑️ Delete Place", key=f"delp_{idx}_{st.session_state.current_project}"):
                    st.session_state["del_place"] = idx
    
    if "del_place" in st.session_state:
        idx = st.session_state.del_place
        st.warning(f"Delete place **{data['places'][idx].get('name')}**?")
        if st.button("Yes, delete"):
            del data["places"][idx]
            save_project(st.session_state.current_project, data)
            del st.session_state.del_place
            st.rerun()
        if st.button("Cancel"):
            del st.session_state.del_place
            st.rerun()
    
    if st.button("🔄 AI Update Places from Manuscript"):
        full_text = "\n\n".join(ch["content"] for ch in data["chapters"])
        prompt = f"Extract and richly describe every location. Check consistency.\nManuscript: {full_text[:15000]}"
        with st.spinner("Analyzing..."):
            result = call_grok(prompt, temperature=0.3)
        st.info(result)

# TAB 3: STORY STRUCTURE
with tab3:
    st.subheader("📋 Story Structure")
    for section_key, section_title in [("plot", "Plot"), ("storyline", "Storyline"), ("outline", "Outline")]:
        st.subheader(section_title)
        if st.button(f"➕ Add New {section_title}", key=f"add_{section_key}_{st.session_state.current_project}"):
            data[section_key].append({"title": f"New {section_title} Point", "description": ""})
            save_project(st.session_state.current_project, data)
            st.rerun()
        for idx, item in enumerate(data[section_key]):
            with st.expander(f"{item.get('title', 'Unnamed')}", expanded=False):
                col1, col2 = st.columns([4, 1])
                with col1:
                    item["title"] = st.text_input("Title", item.get("title", ""), key=f"{section_key}_title_{idx}_{st.session_state.current_project}")
                    item["description"] = st.text_area("Description", item.get("description", ""), height=180, key=f"{section_key}_desc_{idx}_{st.session_state.current_project}")
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{section_key}_{idx}_{st.session_state.current_project}"):
                        st.session_state[f"confirm_del_{section_key}"] = idx
        
        if f"confirm_del_{section_key}" in st.session_state:
            idx = st.session_state[f"confirm_del_{section_key}"]
            st.warning(f"Delete **{data[section_key][idx].get('title')}**?")
            if st.button("Yes, delete"):
                del data[section_key][idx]
                save_project(st.session_state.current_project, data)
                del st.session_state[f"confirm_del_{section_key}"]
                st.rerun()
            if st.button("Cancel"):
                del st.session_state[f"confirm_del_{section_key}"]
                st.rerun()
        
        if st.button(f"🔄 AI Update {section_title} from Manuscript", key=f"ai_{section_key}_{st.session_state.current_project}"):
            full_text = "\n\n".join(ch["content"] for ch in data["chapters"])
            prompt = f"Improve and expand the {section_title} based on the full manuscript.\nManuscript: {full_text[:12000]}"
            with st.spinner("Updating..."):
                result = call_grok(prompt, temperature=0.4)
            st.info(result)

# TAB 4: AI TOOLS
with tab4:
    st.subheader("Global AI Tools")
    if st.button("📊 Full Manuscript Analysis"):
        full_text = "\n\n".join(ch["content"] for ch in data["chapters"])
        with st.spinner("Analyzing..."):
            st.markdown(call_grok(f"Give professional editorial analysis:\n{full_text[:15000]}"))
    
    if st.button("🪄 Generate Next Chapter"):
        full_text = "\n\n".join(ch["content"] for ch in data["chapters"])
        style = f"Match this style: {data.get('style_reference', '')}" if data.get("style_reference") else ""
        prompt = f"{style}\nWrite the next chapter:\n{full_text[-10000:]}"
        with st.spinner("Writing..."):
            result = call_grok(prompt)
            data["chapters"].append({"title": f"Chapter {len(data['chapters'])+1}", "content": result})
            save_project(st.session_state.current_project, data)
        st.rerun()
    
    st.subheader("Compare Projects")
    project_files = [f[:-5] for f in os.listdir("projects") if f.endswith(".json")]
    other = st.selectbox("Compare with another project", ["(none)"] + [p for p in project_files if p != st.session_state.current_project])
    if other != "(none)" and st.button("Compare for consistency"):
        with open(f"projects/{other}.json", "r", encoding="utf-8") as f:
            other_data = json.load(f)
        current_text = "\n\n".join(ch["content"] for ch in data["chapters"])
        other_text = "\n\n".join(ch["content"] for ch in other_data.get("chapters", []))
        prompt = f"Compare these two projects for inconsistencies.\n\nProject 1: {st.session_state.current_project}\n{current_text[:8000]}\n\nProject 2: {other}\n{other_text[:8000]}"
        with st.spinner("Comparing..."):
            st.markdown(call_grok(prompt))

st.success("✅ Full code with Download/Upload, Credit Tracker, and complete isolation loaded.")
