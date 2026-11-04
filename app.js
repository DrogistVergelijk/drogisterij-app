// Zorg dat hier jouw exacte link staat (met /gviz/tq?tqx=out:csv aan het einde)
const SHEET_URL = 'https://docs.google.com/spreadsheets/d/1yXY2u4nidJi7lQcjUciqxc--aHMs24BlrWdp-_0VJI0/edit?usp=sharing/gviz/tq?tqx=out:csv';

let alleProducten = []; // Hier slaan we de producten gratis in op de telefoon

// Deze functie haalt de data op en zet ze om in bruikbare regels
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
    if (row.length > 1 || row[0] !== "") { lines.push(row); }
    return lines;
}

// Producten op het scherm tonen
function toonProducten(productenLijst) {
    const container = document.getElementById('products-container');
    container.innerHTML = ""; // Wis het laad-scherm

    if (productenLijst.length === 0) {
        container.innerHTML = "<p style='text-align:center; color:#888;'>Geen producten gevonden...</p>";
        return;
    }

    productenLijst.forEach(prod => {
        let actieBadge = "";
        // Als er een actie-aantal en actieprijs is (bijv 3 voor 11), toon de badge!
        if (prod.actieAantal && prod.actiePrijs && prod.actieAantal.trim() !== "" && prod.actiePrijs.trim() !== "") {
            actieBadge = `<div class="badge">🔥 ACTIE: ${prod.actieAantal} voor €${prod.actiePrijs}</div>`;
        }

        container.innerHTML += `
            <div class="product-card">
                <div class="title">${prod.naam}</div>
                <div class="price">Stukprijs: ${prod.prijs}</div>
                ${actieBadge}
                <a href="${prod.link}" target="_blank" class="btn">Bekijk bij Drogisterij</a>
            </div>
        `;
    });
}

// Live inladen vanuit Google Sheets
async function startApp() {
    const container = document.getElementById('products-container');
    container.innerHTML = "<p style='text-align:center;'>Producten live laden uit database...</p>";

    try {
        const response = await fetch(SHEET_URL);
        const csvTekst = await response.text();
        
        const data = parseCSV(csvTekst);
        const rijen = data.slice(1); // Sla de eerste rij met kolomnamen over

        alleProducten = rijen.map(kolommen => {
            return {
                id: kolommen[0] || "",
                naam: kolommen[1] || "",
                link: kolommen[2] || "#",
                actieAantal: kolommen[3] || "",
                actiePrijs: kolommen[4] || "",
                prijs: kolommen[5] || ""
            };
        }).filter(p => p.naam.trim() !== ""); // Filter lege regels eruit

        // Toon direct alle 24 producten bij de start
        toonProducten(alleProducten);

        // Activeer de gratis zoekbalk
        document.getElementById('search').addEventListener('input', (e) => {
            const zoekterm = e.target.value.toLowerCase();
            const gefilterd = alleProducten.filter(p => p.naam.toLowerCase().includes(zoekterm));
            toonProducten(gefilterd);
        });

    } catch (fout) {
        container.innerHTML = "<p style='color:red; text-align:center;'>Fout bij laden van live data. Controleer je link.</p>";
        console.error(fout);
    }
}

startApp();
