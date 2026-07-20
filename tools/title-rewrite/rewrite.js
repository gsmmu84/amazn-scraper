// MMU full-catalog title rewrite engine v2
const fs = require("fs");
const path = require("path");
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "catalog.json"), "utf8"));

const strip = (s) => s.replace(/\s+/g, " ").trim();

function stripBrand(t) {
  let s = t;
  s = s.replace(/^magnet me up[:,]?\s*/i, "");
  s = s.replace(/\s*[-–|,]?\s*magnet me up\s*$/i, "");
  s = s.replace(/^ships next day[:,]?\s*/i, "");
  return strip(s);
}

function extractSize(t) {
  let m = t.match(/(\d+(?:\.\d+)?)\s*["”']?\s*x\s*(\d+(?:\.\d+)?)\s*(?:["”']|inch(?:es)?|in\b)?/i);
  if (m) return { txt: `${m[1]}x${m[2]} Inch`, raw: m[0] };
  m = t.match(/(\d+(?:\.\d+)?)\s*(?:["”]|inch(?:es)?\b|in\b(?!\w))/i);
  if (m) return { txt: `${m[1]} Inch`, raw: m[0] };
  return null;
}

function extractPack(t) {
  let m = t.match(/(\d+)\s*[- ]?(?:pack|pk)\b/i);
  if (m) return { n: +m[1], txt: +m[1] === 1 ? "" : `${m[1]} Pack`, raw: m[0] };
  m = t.match(/(\d+)\s*[- ]?(?:count|ct)\b/i);
  if (m) return { n: +m[1], txt: `${m[1]} ct`, raw: m[0] };
  m = t.match(/(\d+)\s*[- ]?(?:piece|pc|pcs)\b/i);
  if (m) return { n: +m[1], txt: `${m[1]} pc`, raw: m[0] };
  return null;
}

const NOISE = /\b(heavy[- ]duty|durable|premium|perfect|ideal|great|amazing|proudly|demonstrate|showcase|display your|any (other )?magnetic surface|magnetic surface|automotive|accessor(y|ies))\b/gi;

function claimsUSA(t) { return /(made|crafted) in (the )?usa/i.test(t); }

// what IS this product? pick the noun buyers search
function productNoun(t) {
  const pairs = [
    [/business card/i, "Business Card Magnets"],
    [/magnet(ic)? (strip|tape)|magnet tape/i, "Magnetic Tape"],
    [/name tag|name badge|badge/i, "Name Tag Badge"],
    [/luggage tag/i, "Luggage Tag"],
    [/golf ball/i, "Golf Ball"],
    [/metal sign|aluminum sign/i, "Metal Sign"],
    [/cruise/i, "Cruise Door Magnet"],
    [/dishwasher/i, "Dishwasher Magnet"],
    [/photo magnet|picture magnet|photo booth|wallet size photo/i, "Photo Magnet"],
    [/(fridge|refrigerator) magnet/i, "Fridge Magnet"],
    [/locker/i, "Locker Magnet"],
    [/door magnet/i, "Door Magnet"],
  ];
  for (const [re, noun] of pairs) if (re.test(t)) return noun;
  if (/car|truck|suv|vehicle|bumper|automotive/i.test(t)) return "Car Magnet";
  return "Magnet";
}

function extractDesign(t) {
  let s = stripBrand(t);
  const sz = extractSize(s); if (sz) s = s.replace(sz.raw, " ");
  const pk = extractPack(s); if (pk) s = s.replace(pk.raw, " ");
  s = s.replace(/\d+(?:\.\d+)?\s*(?:inch(?:es)?|["”])/gi, " ");
  s = s.split(/ [-–—] |, | \| |\(/)[0];
  s = s.replace(/\b(magnet(ic)?( decal)?s?|decals?|vinyl|sign)\b.*$/i, "");
  s = s.replace(NOISE, "");
  s = s.replace(/\b(for )?(car|truck|suv|refrigerator|fridge)s?\b\s*$/gi, "");
  return strip(s.replace(/[,\-–]+$/, ""));
}

function assemble(core, hook, trust) {
  const b = (h, tr) => [core, h, tr].filter(Boolean).join(", ");
  let t = b(hook, trust);
  if (t.length <= 75) return t;
  if (trust === "Made in USA") { t = b(hook, "USA Made"); if (t.length <= 75) return t; }
  t = b(hook, null); if (t.length <= 75) return t;
  t = b(null, trust ? "USA Made" : null); if (t.length <= 75) return t;
  return core;
}

// shrink a design string that makes core too long; keep noun+size intact
function fitCore(design, tail, budget, notes) {
  let d = design;
  const build = () => strip(`${d} ${tail}`);
  if (build().length <= budget) return build();
  // targeted shrinks for known verbose patterns
  const shrinks = [
    [/\bsupport\b /i, ""], [/\bawareness\b /i, ""],
    [/\b(and|&) (ivory|white|gold|silver|lavender|periwinkle|zebra|orange|lime|burgundy|teal|pink|blue|green|purple|red|yellow|gray|grey|black|pearl)\b ?/i, ""],
    [/\b(burgundy|ivory|lime|lavender|periwinkle|zebra|pearl) /i, ""],
    [/\bsticker(s)? and\b.*?(?=ribbon|oval|car|magnet|$)/i, ""],
  ];
  for (const [re, rep] of shrinks) {
    if (build().length <= budget) break;
    const nd = strip(d.replace(re, rep));
    if (nd.length < d.length && nd.length > 5) d = nd;
  }
  // before trimming design words, try downgrading the size unit (Inch → in)
  if (/ Inch\b/.test(tail)) {
    const t2 = tail.replace(/ Inch\b/g, " in");
    if (strip(`${d} ${t2}`).length <= budget) return strip(`${d} ${t2}`);
  }
  // last resort: drop words from the END of design (size/noun preserved in tail)
  let words = d.split(" ");
  while (words.length > 2 && strip(`${words.join(" ")} ${tail}`).length > budget) words.pop();
  d = words.join(" ");
  notes.push("design shortened");
  return strip(`${d} ${tail}`);
}

const IMPORTANT = ["decal","magnetic","weatherproof","waterproof","vinyl","fridge","refrigerator","truck","suv","gift","uv","locker","mailbox","bumper","personalized","custom"];
function missingTokens(orig, title, ih) {
  const has = (s, w) => new RegExp("\\b" + w, "i").test(s);
  return IMPORTANT.filter(w => has(orig, w) && !has(title, w) && !has(ih, w));
}

function rewrite(rec) {
  const orig = rec.title;
  const t = orig;
  const stripped = stripBrand(t);
  const size = extractSize(stripped);
  const pack = extractPack(stripped);
  const usa = claimsUSA(t);
  const trust = usa ? "Made in USA" : null;
  const noun = productNoun(t);
  let family, core, hook, ih, conf = "HIGH", notes = [];
  const sz = size ? size.txt : "";
  const pk = pack && pack.txt ? pack.txt : "";
  const szpk = strip([sz, pk].join(" "));

  if (noun === "Business Card Magnets") {
    family = "Business Card";
    const ct = pack ? `${pack.n} ct` : "";
    core = strip(`Custom Business Card Magnets ${ct} ${sz || "3.5x2 Inch"} 30 Mil`);
    hook = "Upload Logo";
    ih = "Magnetic business cards | Upload image & text | Heavy duty strong hold | Advertising & branding";
  } else if (noun === "Cruise Door Magnet") {
    family = "Cruise";
    let d = extractDesign(t).replace(/\b(custom(izable)?|personalized|cruise|door|ship|cabin|stateroom|magnets?)\b/gi, " ");
    d = strip(d).replace(/^[,\s]+|[,\s]+$/g, "");
    if (!d) { d = "Custom"; conf = "MEDIUM"; }
    core = fitCore(d, `Cruise Door Magnet ${szpk}`, 75 - ", Personalized".length, notes);
    hook = "Personalized";
    ih = "Cruise ship cabin & stateroom door decoration | Add name & text | Full color UV printed";
  } else if (/\bamerican flag\b/i.test(t) && !/christmas/i.test(t)) {
    family = "Flag-US";
    // qualifier keeps variants distinct (distressed, reversed, black & white...)
    let q = "";
    const qm = t.match(/\b(distressed|reversed|black and white|black & white|subdued|vertical|waving|tattered|vintage|thin (blue|red|green) line|opposing|patriotic scroll|betsy ross|gadsden|police|firefighter)\b/i);
    if (qm) q = qm[0].replace(/\b\w/g, c => c.toUpperCase()) + " ";
    if (/\+\s*reversed|and reversed/i.test(t)) q = "+ Reversed ";
    core = strip(`${q}American Flag Car Magnet ${szpk}`);
    hook = "Red White & Blue";
    ih = "Heavy duty magnetic decal for car, truck, SUV, mailbox or any magnetic surface | Patriotic gift";
  } else if (/\bflag\b/i.test(t)) {
    family = "Flag-Other";
    let d = extractDesign(t).replace(/\bflag\b.*$/i, "").trim();
    if (!d) { d = "Flag"; conf = "REVIEW"; }
    core = fitCore(d, `Flag Car Magnet ${szpk}`, usa ? 75 - ", USA Made".length : 75, notes);
    hook = null;
    ih = "Heavy duty magnetic decal for car, truck, SUV or any magnetic surface | Vivid UV printed colors";
  } else if (/color your own/i.test(t)) {
    family = "Color Your Own";
    let d = stripBrand(t).replace(/^color your own\s*/i, "").split(/ DIY| Coloring| Magnet|,/i)[0];
    core = strip(`Color Your Own ${strip(d)} Magnet ${sz || "5x7 Inch"}`);
    hook = "Kids DIY Craft";
    ih = "DIY coloring magnet decal | Creative activity & gift for kids | Fridge or locker decoration";
  } else if (noun === "Golf Ball") {
    family = "Golf Ball";
    const p2 = pack ? `${pack.n} Pack` : "";
    const side = /front side/i.test(t) ? "Front Print" : "";
    core = strip(`Custom Photo Golf Ball ${p2} ${side}`);
    hook = "Add Logo & Text";
    ih = "Personalized golf ball with 1.25 Inch full color UV printed design | Gift for golfers";
  } else if (noun === "Metal Sign") {
    family = "Metal Sign";
    core = strip(`Custom Metal Sign ${szpk}`);
    hook = "Upload Logo & Text";
    ih = "Customizable aluminum sign for home, business, office or garage | Indoor & outdoor";
  } else if (noun === "Photo Magnet") {
    family = "Photo Magnet";
    let theme = "";
    for (const th of ["Christmas","Hanukkah","Halloween","Thanksgiving","Rosh Hashanah"]) if (new RegExp(th, "i").test(t)) { theme = th + " "; break; }
    let variant = "";
    const vm = t.match(/\b(santa|snow border|gingerbread( man)?|ornaments?|candy cane|red frame|sage green|blue|pumpkin|witch|autumn leaves|fruits and vegetables|menorah|photo booth|wallet size)\b/i);
    if (vm) variant = vm[0].replace(/\b\w/g, c => c.toUpperCase());
    core = strip(`Custom ${theme}Photo Magnet ${sz} ${pk}${variant ? ", " + variant : ""}`);
    hook = "Add Photo & Text";
    ih = "Personalized picture refrigerator magnet | Full color UV printed durable vinyl | Keepsake gift";
  } else if (/\b(caution|new driver|student driver|baby on board|frequent stops|delivery driver)\b/i.test(t)) {
    family = "Driver/Novelty";
    let d = extractDesign(t);
    core = fitCore(d, `Car Magnet ${szpk}`, 75, notes);
    hook = /new driver|student driver/i.test(t) ? "Funny Student Driver" : (/funny|embarrassed|gag/i.test(t) ? "Funny" : null);
    ih = "Heavy duty magnetic decal for car or any magnetic surface | UV printed";
  } else if (/\b(custom|customizable|personalized)\b/i.test(t) && /(car magnet|vehicle|magnetic sign|car sign)/i.test(t) && noun === "Car Magnet") {
    family = "Custom Vehicle";
    const round = /round/i.test(t) ? "Round " : /die[- ]?cut/i.test(t) ? "Die Cut " : "";
    const mil = /30 mil/i.test(t) ? "30 Mil" : "";
    core = strip(`Custom ${round}Car Magnet ${sz} ${mil} ${pk}`);
    hook = "Upload Logo";
    ih = "Personalized magnetic business sign for vehicles & trucks | Add your text | Weatherproof";
  } else if (/\b(pawprint|paw print|dog bone|dog|puppy|cat|kitten|pet)s?\b/i.test(t)) {
    family = "Dog/Paw";
    let d = extractDesign(t);
    const isDog = /\b(dog|puppy|pawprint|paw print)\b/i.test(t);
    const isCat = /\b(cat|kitten)\b/i.test(t) && !isDog;
    hook = isDog ? "Dog Lover Gift" : isCat ? "Cat Lover Gift" : null;
    core = fitCore(d, `${noun} ${szpk}`, hook ? 75 - (", " + hook).length : 75, notes);
    ih = "Heavy duty magnetic decal for car, truck, SUV or fridge | Full color UV printed";
  } else {
    family = "General Magnet";
    let d = extractDesign(t);
    if (!d || d.length < 3) { d = stripBrand(t).split(/[,\-–]/)[0]; conf = "MEDIUM"; }
    hook = /\b(funny|gag|sarcastic)\b/i.test(t) ? "Funny Gift" : null;
    core = fitCore(d, `${noun} ${szpk}`, hook ? 75 - (", " + hook).length : 75, notes);
    ih = noun === "Car Magnet"
      ? "Heavy duty magnetic decal for car, truck, SUV, fridge or any magnetic surface"
      : "Heavy duty magnet | Full color UV printed | Made to order";
    conf = conf === "HIGH" ? "MEDIUM" : conf;
  }

  if (assemble(core, hook, trust).length > 75 && / Inch\b/.test(core)) { const c2 = core.replace(/ Inch\b/g, " in"); if (assemble(c2, hook, trust).length <= 75) core = c2; }
  let title = assemble(core, hook, trust);
  if (title.length > 75) { title = title.slice(0, 75).replace(/\s+\S*$/, ""); conf = "REVIEW"; notes.push("hard trim"); }
  title = strip(title.replace(/\s+,/g, ","));
  ih = ih.split(" | ").map((s, i) => {
    if (i === 0) return s;
    return /^[A-Z]{2}/.test(s) ? s : s.charAt(0).toLowerCase() + s.slice(1);
  }).join(", ");
  if (ih.length > 125) ih = ih.slice(0, ih.lastIndexOf(",", 125)).trim();

  const missing = missingTokens(orig, title, ih);
  if (missing.length > 2) notes.push("tokens lost: " + missing.slice(0, 4).join(","));
  if (!size && !["Business Card","Golf Ball"].includes(family)) { conf = conf === "HIGH" ? "MEDIUM" : conf; notes.push("no size found"); }
  if (rec.skus.length === 0) notes.push("NO SKU — map before upload");
  if (notes.includes("design shortened")) conf = conf === "HIGH" ? "MEDIUM" : conf;
  if (orig.length <= 75) { title = orig; ih = ""; conf = "OK AS-IS"; notes = ["already compliant"]; }

  return { family, title, ih, conf, notes: notes.join("; ") };
}

// run
let out = catalog.map(rec => ({ ...rec, ...rewrite(rec) }));

// dedup pass: distinct ASINs must not share a title
const groups = new Map();
out.forEach((r, i) => { if (r.conf === "OK AS-IS") return; (groups.get(r.title) || groups.set(r.title, []).get(r.title)).push(i); });
const STOP = new Set(["magnet","me","up","the","a","an","and","or","for","of","with","in","on","your","to","car","truck","suv","magnetic","decal","magnets","decals","pack","inch","inches","made","usa","heavy","duty","2","3","4","5","any","other","surface","surfaces","mailbox","mailboxes","gift","vinyl","uv","printed","weatherproof","waterproof","durable","red","white","blue","color","full","display","auto","automotive","vehicles","vehicle","fridge","refrigerator","refrigerators","patriotic","patriotism","american","flag","flags"]);
let dupFixed = 0, dupLeft = 0;
for (const [title, idxs] of groups) {
  if (idxs.length < 2) continue;
  // token sets per member
  const toks = idxs.map(i => new Set(out[i].title.toLowerCase().match(/[a-z0-9.']+/g) || []));
  const origToks = idxs.map(i => (catalog.find(c => c.asin === out[i].asin).title.toLowerCase().match(/[a-z0-9.']+/g) || []));
  idxs.forEach((i, k) => {
    // distinctive words: in my orig, not in any other member's orig
    const others = new Set(origToks.flatMap((o, j) => j === k ? [] : o));
    const distinct = origToks[k].filter(w => !others.has(w) && !STOP.has(w) && w.length > 2 && !/^\d+$/.test(w));
    if (k === 0) return; // first keeps clean title
    if (distinct.length) {
      const add = distinct.slice(0, 2).map(w => w.replace(/\b\w/g, c => c.toUpperCase())).join(" ");
      const r = out[i];
      const parts = r.title.split(", ");
      parts[0] = strip(add + " " + parts[0]);
      let nt = parts.join(", ");
      while (nt.length > 75 && parts.length > 1) { parts.pop(); nt = parts.join(", "); }
      if (nt.length <= 75) { r.title = nt; r.notes = strip(r.notes + "; disambiguated"); dupFixed++; return; }
    }
    out[i].conf = "REVIEW"; out[i].notes = strip(out[i].notes + "; duplicate title — distinguish manually"); dupLeft++;
  });
}

fs.writeFileSync(path.join(__dirname, "rewritten.json"), JSON.stringify(out));

const confCount = {}, famCount = {};
let over = 0;
for (const r of out) {
  confCount[r.conf] = (confCount[r.conf] || 0) + 1;
  famCount[r.family] = (famCount[r.family] || 0) + 1;
  if (r.conf !== "OK AS-IS" && r.title.length > 75) over++;
}
// remaining dupes
const m2 = new Map(); out.forEach(r => { if (r.conf === "OK AS-IS") return; m2.set(r.title, (m2.get(r.title) || 0) + 1); });
const remaining = [...m2.values()].filter(c => c > 1).length;
console.log("confidence:", JSON.stringify(confCount));
console.log("families:", JSON.stringify(famCount));
console.log("over75:", over, "| dupes fixed:", dupFixed, "| dupes left(REVIEW):", dupLeft, "| dup groups remaining:", remaining);
