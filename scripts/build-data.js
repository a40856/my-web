#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');

const SOURCES = [
  {
    id: 'active',
    title: '熱門期權（Active）',
    srcDir: path.join(__dirname, '..', 'testing', 'active'),
    filePattern: /^Mostactive-.*\.xlsx$/i,
    dataOutput: path.join(__dirname, '..', 'docs', 'data', 'active.json'),
    assetDir: path.join(__dirname, '..', 'docs', 'data', 'latest', 'active')
  },
  {
    id: 'history',
    title: '股票觀察名單（History）',
    srcDir: path.join(__dirname, '..', 'testing', 'history'),
    filePattern: /^final_stock_data-.*\.xlsx$/i,
    dataOutput: path.join(__dirname, '..', 'docs', 'data', 'history.json'),
    assetDir: path.join(__dirname, '..', 'docs', 'data', 'latest', 'history')
  },
  {
    id: 'oi',
    title: '最高未平倉量（OI）',
    srcDir: path.join(__dirname, '..', 'testing', 'OI'),
    filePattern: /^Sorted-.*\.xlsx$/i,
    dataOutput: path.join(__dirname, '..', 'docs', 'data', 'oi.json'),
    assetDir: path.join(__dirname, '..', 'docs', 'data', 'latest', 'oi')
  }
];

function ensureDir(dirPath){
  fs.mkdirSync(dirPath, { recursive: true });
}

function findLatestFile(dirPath, pattern){
  if(!fs.existsSync(dirPath)) return null;
  const entries = fs.readdirSync(dirPath).filter(name => pattern.test(name));
  if(entries.length === 0) return null;
  const withStats = entries.map(name => {
    const fullPath = path.join(dirPath, name);
    const stats = fs.statSync(fullPath);
    return { name, fullPath, stats };
  });
  withStats.sort((a, b) => {
    const nameCompare = a.name.localeCompare(b.name);
    if(nameCompare !== 0) return nameCompare;
    return a.stats.mtimeMs - b.stats.mtimeMs;
  });
  return withStats[withStats.length - 1];
}

function sheetRows(workbook){
  const sheetName = workbook.SheetNames[0];
  if(!sheetName) return [];
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false });
  return rows
    .map(row => Array.isArray(row) ? row.map(cell => cell == null ? '' : String(cell)) : [])
    .filter(row => row.some(cell => cell.trim() !== ''));
}

function buildSource(source){
  const latest = findLatestFile(source.srcDir, source.filePattern);
  if(!latest){
    console.warn(`[warn] ${source.id}: no files matching pattern.`);
    return null;
  }

  const workbook = XLSX.readFile(latest.fullPath);
  const rows = sheetRows(workbook);
  ensureDir(path.dirname(source.dataOutput));
  ensureDir(source.assetDir);

  const destName = latest.name;
  const destPath = path.join(source.assetDir, destName);

  // Remove existing files in asset dir to keep only the latest copy
  for(const existing of fs.readdirSync(source.assetDir)){
    fs.rmSync(path.join(source.assetDir, existing));
  }
  fs.copyFileSync(latest.fullPath, destPath);

  const payload = {
    id: source.id,
    title: source.title,
    generatedAt: new Date().toISOString(),
    sourceFile: latest.name,
    download: path.relative(path.join(__dirname, '..', 'docs'), destPath).replace(/\\/g, '/'),
    rows
  };

  fs.writeFileSync(source.dataOutput, JSON.stringify(payload, null, 2));
  console.log(`[ok] ${source.id}: wrote ${payload.rows.length} rows from ${latest.name}`);
  return payload;
}

(function main(){
  const results = SOURCES.map(buildSource).filter(Boolean);
  if(results.length === 0){
    console.error('No data files processed.');
    process.exitCode = 1;
  }
})();
