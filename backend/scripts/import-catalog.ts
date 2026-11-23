import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';

const prisma = new PrismaClient();

const CHUNK_SIZE = 1000;

function slugify(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function clean(value: unknown): string {
  return typeof value === 'string' ? value.replace(/\u0000/g, '').trim() : '';
}

async function main() {
  const limitArg = process.argv.find((arg) => arg.startsWith('--limit='));
  const limit = limitArg ? Number(limitArg.split('=')[1]) : 0;

  const aiDir = path.resolve(__dirname, '../../ai-service');
  const masterPath = path.join(aiDir, 'data/master/perfumes_master.csv');
  const fallbackPath = path.join(aiDir, 'data/perfumes.csv');
  const dataPath = fs.existsSync(masterPath) ? masterPath : fallbackPath;

  if (!fs.existsSync(dataPath)) {
    throw new Error(`No se encontró el dataset: ${dataPath}`);
  }

  console.log(`Leyendo catálogo: ${dataPath}`);
  const raw = fs.readFileSync(dataPath, 'utf-8');
  let rows = parse(raw, {
    delimiter: '|',
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    relax_quotes: true,
    bom: true,
  }) as Record<string, string>[];

  if (limit > 0) {
    rows = rows.slice(0, limit);
  }

  console.log(`Filas leídas: ${rows.length}`);

  const seen = new Map<string, number>();
  const records: {
    externalId: string;
    brand: string;
    name: string;
    family: string | null;
    subfamily: string | null;
    gender: string | null;
    releaseYear: string | null;
    description: string | null;
    imageUrl: string | null;
  }[] = [];

  for (const row of rows) {
    const brand = clean(row.brand) || 'Unknown';
    const name = clean(row.name_perfume) || clean(row.name);
    if (!name) {
      continue;
    }

    const baseId = `${slugify(brand)}--${slugify(name)}`;
    if (!baseId || baseId === '--') {
      continue;
    }

    // Misma resolución de colisiones que train.py para que los IDs
    // coincidan exactamente con los del modelo TF-IDF.
    let externalId = baseId;
    if (seen.has(baseId)) {
      const count = seen.get(baseId)! + 1;
      seen.set(baseId, count);
      externalId = `${baseId}-${count}`;
    } else {
      seen.set(baseId, 0);
    }

    const imageName = clean(row.image_name);
    records.push({
      externalId,
      brand,
      name,
      family: clean(row.family) || null,
      subfamily: clean(row.subfamily) || null,
      gender: clean(row.gender) || null,
      releaseYear: clean(row.years) || null,
      description: clean(row.description) || null,
      imageUrl: imageName.startsWith('http') ? imageName : null,
    });
  }

  console.log(`Perfumes únicos a importar: ${records.length}`);

  let inserted = 0;
  for (let i = 0; i < records.length; i += CHUNK_SIZE) {
    const chunk = records.slice(i, i + CHUNK_SIZE);
    const result = await prisma.perfume.createMany({
      data: chunk,
      skipDuplicates: true,
    });
    inserted += result.count;
    console.log(`  ${Math.min(i + CHUNK_SIZE, records.length)} / ${records.length} procesados (${inserted} nuevos)`);
  }

  const total = await prisma.perfume.count();
  console.log(`\nCatálogo importado. Insertados en esta ejecución: ${inserted}`);
  console.log(`Total de perfumes en la base de datos: ${total}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
