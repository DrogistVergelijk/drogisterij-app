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

// Slimme rekenhulp die de actuele prijs berekent om mee te sorteren
function geefHuidigePrijsGetal(prod) {
    // Als er een geldige actie-prijs (E) is, gebruiken we die!
    if (prod.actieDeal && prod.actieDeal.trim() !== "" && !isNaN(parseFloat(prod.actieDeal.replace(',', '.')))) {
        return parseFloat(prod.actieDeal.replace(',', '.'));
    }
    // Anders vallen we terug op de originele prijs (F)
    if (prod.prijs) {
        let opgeschoond = prod.prijs.toString().replace(/[^0-9\.,]/g, '').replace(',', '.');
        let nummer = parseFloat(opgeschoond);
        return isNaN(nummer) ? 9999 : nummer;
    }
    return 9999;
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
        let prijsWeergave = `<div class="price" style="color:#2ecc71; font-weight:bold; margin:5px 0;">Stukprijs: ${prod.prijs}</div>`;
        
        // Als er een actie en een dealprijs is (bijv. 3 voor €11)
        if (prod.actie && prod.actie.trim() !== "" && prod.actie !== "undefined") {
            let dealTekst = (prod.actieDeal && prod.actieDeal.trim() !== "" && prod.actieDeal !== "undefined")
                ? `${prod.actie} ${prod.actieDeal}`
                : prod.actie;
            
            if (prod.actie.toLowerCase().includes('voor') && !prod.actieDeal.includes('€')) {
                dealTekst = `${prod.actie} €${prod.actieDeal}`;
            }
            
            actieBadge = `<div class="badge" style="background:#e74c3c; color:white; padding:4px 8px; border-radius:4px; font-size:12px; display:inline-block; margin-top:5px; font-weight:bold;">🔥 ACTIE: ${dealTekst}</div>`;
            
            // Als er een actieprijs is, tonen we de originele prijs doorgestreept en de actieprijs dikgedrukt!
            if (prod.actieDeal && prod.actieDeal.trim() !== "" && prod.actieDeal !== "undefined") {
                prijsWeergave = `
                    <div class="price" style="margin:5px 0;">
                        <span style="text-decoration: line-through; color: #888; font-size: 14px; margin-right: 8px;">Oud: ${prod.prijs}</span>
                        <span style="color:#2ecc71; font-weight:bold; font-size: 18px;">Nu: €${prod.actieDeal}</span>
                    </div>
                `;
            }
        }

        container.innerHTML += `
            <div class="product-card" style="background:white; padding:15px; border-radius:8px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee;">
                <div class="title" style="font-size:18px; font-weight:bold; color:#2c3e50;">${prod.naam}</div>
                ${prijsWeergave}
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

        const idIdx = 0; // Kolom A
        const naamIdx = 1; // Kolom B
        const linkIdx = 2; // Kolom C
        const actieIdx = 3; // Kolom D
        const actieDealIdx = 4; // Kolom E
        const prijsIdx = 5; // Kolom F

        const rijen = data.slice(1);
        alleProducten = rijen.map(kolommen => {
            if (!kolommen || kolommen.length < 2) return null;
            return {
                id: kolommen[idIdx] ? kolommen[idIdx].toString().trim() : "",
                naam: kolommen[naamIdx] ? kolommen[naamIdx].toString().trim() : "",
                link: kolommen[linkIdx] ? kolommen[linkIdx].toString().trim() : "#",
                actie: kolommen[actieIdx] ? kolommen[actieIdx].toString().trim() : "",
                actieDeal: kolommen[actieDealIdx] ? kolommen[actieDealIdx].toString().trim() : "",
                prijs: kolommen[prijsIdx] ? kolommen[prijsIdx].toString().trim() : ""
            };
        }).filter(p => p && p.naam && p.naam !== "");

        // Sorteer op basis van de slimme actuele prijs (eerst actieprijs, anders originele prijs)
        alleProducten.sort((a, b) => geefHuidigePrijsGetal(a) - geefHuidigePrijsGetal(b));

        toonProducten(alleProducten);

        document.getElementById('search').addEventListener('input', (e) => {
            const zoekterm = e.target.value.toLowerCase();
            const gefilterd = alleProducten.filter(p => p.naam.toLowerCase().includes(zoekterm));
            gefilterd.sort((a, b) => geefHuidigePrijsGetal(a) - geefHuidigePrijsGetal(b));
            toonProducten(gefilterd);
        });
    } catch (fout) {
        container.innerHTML = "<p style='color:red; text-align:center;'>De database is momenteel niet bereikbaar.</p>";
    }
}
startApp();
