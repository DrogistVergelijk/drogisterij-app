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
        let actieBadge = prod.actie ? `<div class="badge" style="background:#e74c3c; color:white; padding:4px 8px; border-radius:4px; font-size:12px; display:inline-block; margin-top:5px;">🔥 ACTIE: ${prod.actie}</div>` : "";
        container.innerHTML += `
            <div class="product-card" style="background:white; padding:15px; border-radius:8px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                <div class="title" style="font-size:18px; font-weight:bold;">${prod.naam}</div>
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

        // We zoeken automatisch in welke kolommen de data staat op basis van jouw Rij 1!
        const headers = data[0].map(h => h.toLowerCase().trim());
        const idIdx = headers.findIndex(h => h.includes('id'));
        const naamIdx = headers.findIndex(h => h.includes('naam') || h.includes('title') || h.includes('product'));
        const linkIdx = headers.findIndex(h => h.includes('link') || h.includes('url') || h.includes('href'));
        const prijsIdx = headers.findIndex(h => h.includes('prijs') || h.includes('price') || h.includes('bedrag'));
        const actieIdx = headers.findIndex(h => h.includes('actie') || h.includes('aantal'));

        const rijen = data.slice(1);
        alleProducten = rijen.map(kolommen => {
            return {
                id: idIdx !== -1 ? kolommen[idIdx] : "",
                naam: naamIdx !== -1 ? kolommen[naamIdx] : "",
                link: linkIdx !== -1 ? kolommen[linkIdx] : "#",
                prijs: prijsIdx !== -1 ? kolommen[prijsIdx] : "Op aanvraag",
                actie: actieIdx !== -1 ? kolommen[actieIdx] : ""
            };
        }).filter(p => p.naam && p.naam.trim() !== "");

        toonProducten(alleProducten);

        document.getElementById('search').addEventListener('input', (e) => {
            const zoekterm = e.target.value.toLowerCase();
            const gefilterd = alleProducten.filter(p => p.naam.toLowerCase().includes(zoekterm));
            toonProducten(gefilterd);
        });
    } catch (fout) {
        container.innerHTML = "<p style='color:red; text-align:center;'>De database is momenteel niet bereikbaar.</p>";
    }
}
startApp();
