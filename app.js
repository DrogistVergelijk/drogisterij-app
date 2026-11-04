const SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSqCQnmlbT0NkZxWhiL2ysCv23qzaDntXUyMCu7-ZbjstCVy3Z-au6Fw8JH52P5J41sGlWlWyk7dX6G/pub?output=csv';

let alleProducten = [];

// Functie om de officiële Google CSV-tekst netjes op te splitsen in kolommen
function parseCSV(text) {
    let lines = [];
    let row = [""];
    let inQuotes = false;

    for (let i = 0; i < text.length; i++) {
        let c = text[i];
        let next = text[i+1];
        if (c === '"') {
            if (inQuotes && next === '"') { row[row.length - 1] += '"'; i++; }
            else { inQuotes = !inQuotes; }
        } else if (c === ',' && !inQuotes) {
            row.push("");
        } else if ((c === '\r' || c === '\n') && !inQuotes) {
            if (c === '\r' && next === '\n') { i++; }
            lines.push(row);
            row = [""];
        } else {
            row[row.length - 1] += c;
        }
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
        // Controleer of er echt een actie-aantal in jouw spreadsheet staat
        if (prod.actieAantal && prod.actieAantal.trim() !== "" && prod.actieAantal !== "undefined") {
            let badgeTekst = (prod.actiePrijs && prod.actiePrijs.trim() !== "" && prod.actiePrijs !== "undefined") 
                ? `${prod.actieAantal} voor €${prod.actiePrijs}` 
                : prod.actieAantal;
            actieBadge = `<div class="badge">🔥 ACTIE: ${badgeTekst}</div>`;
        }

        container.innerHTML += `
            <div class="product-card" style="background:white; padding:15px; border-radius:8px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                <div class="title" style="font-size:18px; font-weight:bold;">${prod.naam}</div>
                <div class="price" style="color:#2ecc71; font-weight:bold; margin:5px 0;">Stukprijs: ${prod.prijs}</div>
                ${actieBadge}
                <a href="${prod.link}" target="_blank" class="btn" style="display:block; text-align:center; background:#3498db; color:white; padding:10px; border-radius:6px; text-decoration:none; margin-top:10px; font-weight:bold;">Bekijk bij Drogisterij</a>
            </div>
        `;
    });
}

async function startApp() {
    const container = document.getElementById('products-container');
    container.innerHTML = "<p style='text-align:center;'>Producten live laden uit database...</p>";

    try {
        const response = await fetch(SHEET_URL);
        const csvTekst = await response.text();
        
        const data = parseCSV(csvTekst);
        const rijen = data.slice(1); // Sla de header-rij over

        // We koppelen de kolommen exact aan jouw spreadsheet-volgorde:
        // A=ID (0), B=Productnaam (1), C=Link (2), D=Actie aantal (3), E=Actie prijs (4), F=Prijs (5)
        alleProducten = rijen.map(kolommen => {
            if (!kolommen || kolommen.length < 2) return null;
            return {
                id: kolommen[0] ? kolommen[0].toString().trim() : "",
                naam: kolommen[1] ? kolommen[1].toString().trim() : "",
                link: kolommen[2] ? kolommen[2].toString().trim() : "#",
                actieAantal: kolommen[3] ? kolommen[3].toString().trim() : "",
                actiePrijs: kolommen[4] ? kolommen[4].toString().trim() : "",
                prijs: kolommen[5] ? kolommen[5].toString().trim() : ""
            };
        }).filter(p => p && p.naam && p.naam !== "");

        toonProducten(alleProducten);

        // Activeer de live zoekbalk
        document.getElementById('search').addEventListener('input', (e) => {
            const zoekterm = e.target.value.toLowerCase();
            const gefilterd = alleProducten.filter(p => p.naam.toLowerCase().includes(zoekterm));
            toonProducten(gefilterd);
        });

    } catch (fout) {
        container.innerHTML = "<p style='color:red; text-align:center;'>Fout bij laden van live data. Controleer de internetverbinding.</p>";
        console.error(fout);
    }
}

startApp();
