const SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSqCQnmlbT0NkZxWhiL2ysCv23qzaDntXUyMCu7-ZbjstCVy3Z-au6Fw8JH52P5J41sGlWlWyk7dX6G/pub?output=csv';

let alleProducten = [];

function parseCSV(text) {
    let lines = [];
    let row = [""];
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
        let c = text[i]; let next = text[i+1];
        if (c === '"') {
            if (inQuotes && next === '"') { row[row.length - 1] += '"'; i++; }
            else { inQuotes = !inQuotes; }
        } else if (c === ',' && !inQuotes) { row.push(""); }
        else if ((c === '\r' || c === '\n') && !inQuotes) {
            if (c === '\r' && next === '\n') { i++; }
            lines.push(row); row = [""];
        } else { row[row.length - 1] += c; }
    }
    if (row.length > 1 || row !== "") { lines.push(row); }
    return lines;
}

function toonProducten(productenLijst) {
    const container = document.getElementById('products-container');
    container.innerHTML = "";
    if (!productenLijst || productenLijst.length === 0) {
        container.innerHTML = "<p style='text-align:center; color:#888;'>Geen producten gevonden...</p>";
        return;
    }
    productenLijst.forEach(prod => {
        let actieBadge = (prod.actie && prod.actie.trim() !== "" && prod.actie !== "undefined") ? `<div class="badge" style="background:#e74c3c; color:white; padding:4px 8px; border-radius:4px; font-size:12px; display:inline-block; margin-top:5px; font-weight:bold;">🔥 ACTIE: ${prod.actie}</div>` : "";
        
        container.innerHTML += `
            <div class="product-card" style="background:white; padding:15px; border-radius:8px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee;">
                <div class="title" style="font-size:18px; font-weight:bold; color:#2c3e50;">${prod.naam}</div>
                <div class="price" style="color:#2ecc71; font-weight:bold; margin:5px 0;">Prijs: ${prod.prijs}</div>
                ${actieBadge}
                <a href="${prod.link}" target="_blank" class="btn" style="display:block; text-align:center; background:#3498db; color:white; padding:10px; border-radius:6px; text-decoration:none; margin-top:10px; font-weight:bold;">Bekijk bij Webshop</a>
            </div>
        `;
    });
}

async function startApp() {
    const container = document.getElementById('products-container');
    try {
        const response = await fetch(SHEET_URL);
        const csvTekst = await response.text();
        const data = parseCSV(csvTekst);
        if (data.length < 2) return;

        // We zoeken heel breed naar de namen in Rij 1 van je Google Sheet
        const headers = data[0].map(h => h.toLowerCase().trim());
        
        // Als hij de naam niet vindt, gokt hij de meest logische kolom op basis van jouw volgorde!
        const idIdx = headers.findIndex(h => h.includes('id')) !== -1 ? headers.findIndex(h => h.includes('id')) : 0;
        const naamIdx = headers.findIndex(h => h.includes('naam') || h.includes('title') || h.includes('product')) !== -1 ? headers.findIndex(h => h.includes('naam') || h.includes('title') || h.includes('product')) : 1;
        const linkIdx = headers.findIndex(h => h.includes('link') || h.includes('url') || h.includes('href')) !== -1 ? headers.findIndex(h => h.includes('link') || h.includes('url') || h.includes('href')) : 2;
        const actieIdx = headers.findIndex(h => h.includes('actie') || h.includes('aantal')) !== -1 ? headers.findIndex(h => h.includes('actie') || h.includes('aantal')) : 3;
        const prijsIdx = headers.findIndex(h => h.includes('prijs') || h.includes('price') || h.includes('bedrag')) !== -1 ? headers.findIndex(h => h.includes('prijs') || h.includes('price') || h.includes('bedrag')) : 5; // Kolom F is 5

        const rijen = data.slice(1);
        alleProducten = rijen.map(kolommen => {
            if (!kolommen || kolommen.length < 2) return null;
            return {
                id: kolommen[idIdx] ? kolommen[idIdx].toString().trim() : "",
                naam: kolommen[naamIdx] ? kolommen[naamIdx].toString().trim() : "",
                link: kolommen[linkIdx] ? kolommen[linkIdx].toString().trim() : "#",
                actie: actieIdx !== -1 && kolommen[actieIdx] ? kolommen[actieIdx].toString().trim() : "",
                prijs: kolommen[prijsIdx] ? kolommen[prijsIdx].toString().trim() : "Bekijk op site"
            };
        }).filter(p => p && p.naam && p.naam !== "");

        toonProducten(alleProducten);

        document.getElementById('search').addEventListener('input', (e) => {
            const zoekterm = e.target.value.toLowerCase();
            const gefilterd = alleProducten.filter(p => p.naam.toLowerCase().includes(zoekterm));
            toonProducten(gefilterd);
        });
    } catch (fout) {
        container.innerHTML = "<p style='color:red; text-align:center;'>De database is momentevel niet bereikbaar.</p>";
    }
}
startApp();
