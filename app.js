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
        let actieBadge = "";
        // We controleren of er een actie-aantal óf een actie-prijs in jouw spreadsheet staat
        if (prod.actieAantal && prod.actieAantal.trim() !== "" && prod.actieAantal !== "undefined") {
            let badgeTekst = (prod.actiePrijs && prod.actiePrijs.trim() !== "" && prod.actiePrijs !== "undefined") 
                ? `${prod.actieAantal} voor €${prod.actiePrijs}` 
                : prod.actieAantal;
            actieBadge = `<div class="badge" style="background:#e74c3c; color:white; padding:4px 8px; border-radius:4px; font-size:12px; display:inline-block; margin-top:5px; font-weight:bold;">🔥 ACTIE: ${badgeTekst}</div>`;
        }

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

        const headers = data[0].map(h => h.toLowerCase().trim());
        
        // We dwingen de app om exact naar jouw vaste volgorde te kijken:
        // A=ID(0), B=Naam(1), C=Link(2), D=Actie_Aantal(3), E=Actie_Prijs(4), F=Prijs(5)
        const idIdx = 0;
        const naamIdx = 1;
        const linkIdx = 2;
        const actieAantalIdx = 3;
        const actiePrijsIdx = 4;
        const prijsIdx = 5;

        const rijen = data.slice(1);
        alleProducten = rijen.map(kolommen => {
            if (!kolommen || kolommen.length < 2) return null;
            return {
                id: kolommen[idIdx] ? kolommen[idIdx].toString().trim() : "",
                naam: kolommen[naamIdx] ? kolommen[naamIdx].toString().trim() : "",
                link: kolommen[linkIdx] ? kolommen[linkIdx].toString().trim() : "#",
                actieAantal: kolommen[actieAantalIdx] ? kolommen[actieAantalIdx].toString().trim() : "",
                actiePrijs: kolommen[actiePrijsIdx] ? kolommen[actiePrijsIdx].toString().trim() : "",
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
        container.innerHTML = "<p style='color:red; text-align:center;'>De database is momenteel niet bereikbaar.</p>";
    }
}
startApp();
