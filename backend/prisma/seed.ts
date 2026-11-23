import { PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcryptjs';
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();

const SAMPLE_PERFUMES = [
  {
    externalId: 'giorgio-armani--acqua-di-gio-parfum',
    brand: 'Giorgio Armani',
    name: 'Acqua Di Giò Parfum',
    family: 'AROMATIC FOUGERE',
    subfamily: 'WATERY',
    gender: 'Male',
    releaseYear: '2023',
    description: 'Fragancia marina intensa, amaderada y acuática con notas de incienso y romero.',
    opinion: 'LOVE',
    rating: 5,
    personalDescription: 'Mi perfume favorito para verano y calor. Marino fresco inigualable.',
  },
  {
    externalId: 'chanel--bleu-de-chanel-parfum',
    brand: 'Chanel',
    name: 'Bleu De Chanel Parfum',
    family: 'WOODY',
    subfamily: 'AROMATIC',
    gender: 'Male',
    releaseYear: '2018',
    description: 'Una fragancia intensamente amaderada y aromática con notas de sándalo y cedro.',
    opinion: 'LIKE',
    rating: 4,
    personalDescription: 'Muy versátil y elegante para oficina y eventos formales.',
  },
  {
    externalId: 'versace--eros-eau-de-parfum',
    brand: 'Versace',
    name: 'Eros Eau De Parfum',
    family: 'AMBERY (ORIENTAL)',
    subfamily: 'WOODY',
    gender: 'Male',
    releaseYear: '2020',
    description: 'Manzana crujiente, menta, haba tonka y vainilla sensual.',
    opinion: 'LIKE',
    rating: 4,
    personalDescription: 'Excelente proyección para salir de noche y fiestas.',
  },
  {
    externalId: 'creed--aventus-10th-anniversary-edition-2020',
    brand: 'Creed',
    name: 'Aventus 10Th Anniversary Edition 2020',
    family: 'CHYPRE',
    subfamily: 'FRUITY',
    gender: 'Male',
    releaseYear: '2020',
    description: 'Piña ahumada, abedul, bergamota y grosellas negras legendarias.',
    opinion: 'LOVE',
    rating: 5,
    personalDescription: 'Aroma distintivo y poderoso, gran cumplido.',
  },
  {
    externalId: 'fiorucci--wallstreet',
    brand: 'Fiorucci',
    name: 'Wallstreet',
    family: 'FLORAL',
    subfamily: 'AMBERY (ORIENTAL)',
    gender: 'Male',
    releaseYear: '2015',
    description: 'Notas florales pesadas con fondo amaderado sintético.',
    opinion: 'DISLIKE',
    rating: 2,
    personalDescription: 'Demasiado sintético y empalagoso para mi gusto.',
  },
];

async function main() {
  console.log('--- Iniciando Seed de Base de Datos ---');

  // 1. Verificar si ya tenemos el catálogo poblado
  const totalInDb = await prisma.perfume.count();
  console.log(`Perfumes actuales en base de datos: ${totalInDb}`);

  const possiblePaths = [
    path.join(__dirname, 'perfumes.json'),
    path.join(__dirname, '../../ai-service/model/perfumes.json'),
  ];
  const jsonPath = possiblePaths.find((p) => fs.existsSync(p));

  if (totalInDb < 500 && jsonPath) {
    console.log(`Poblando catálogo desde ${jsonPath}...`);
    const raw = fs.readFileSync(jsonPath, 'utf-8');
    const catalog = JSON.parse(raw) as Array<{
      perfumeId: string;
      brand: string;
      name: string;
      family?: string;
      subfamily?: string;
      gender?: string;
      releaseYear?: string;
    }>;

    console.log(`Leídos ${catalog.length} perfumes del modelo. Insertando en lotes...`);
    const CHUNK_SIZE = 5000;
    for (let i = 0; i < catalog.length; i += CHUNK_SIZE) {
      const slice = catalog.slice(i, i + CHUNK_SIZE).map((p) => ({
        externalId: p.perfumeId,
        brand: p.brand || '',
        name: p.name || '',
        family: p.family || null,
        subfamily: p.subfamily || null,
        gender: p.gender || null,
        releaseYear: p.releaseYear || null,
      }));

      await prisma.perfume.createMany({
        data: slice,
        skipDuplicates: true,
      });
      console.log(`  -> Insertados ${Math.min(i + CHUNK_SIZE, catalog.length)} / ${catalog.length}`);
    }
  }

  // 2. Crear usuario demo principal
  console.log('Verificando usuario demo...');
  const passwordHash = await bcrypt.hash('password123', 10);
  const user = await prisma.user.upsert({
    where: { email: 'demo@perfumeadvisor.com' },
    update: { passwordHash },
    create: {
      name: 'Horacio (Demo)',
      email: 'demo@perfumeadvisor.com',
      passwordHash,
    },
  });

  console.log(`Usuario listo: ${user.email} (Contraseña: password123)`);

  // 3. Crear perfumes de muestra en inventario si no existen
  const inventoryCount = await prisma.inventoryItem.count({ where: { userId: user.id } });
  if (inventoryCount === 0) {
    console.log('Agregando perfumes iniciales al inventario del usuario demo...');
    for (const item of SAMPLE_PERFUMES) {
      const perfume = await prisma.perfume.upsert({
        where: { externalId: item.externalId },
        update: {},
        create: {
          externalId: item.externalId,
          brand: item.brand,
          name: item.name,
          family: item.family,
          subfamily: item.subfamily,
          gender: item.gender,
          releaseYear: item.releaseYear,
          description: item.description,
        },
      });

      await prisma.inventoryItem.create({
        data: {
          userId: user.id,
          perfumeId: perfume.id,
          rating: item.rating,
          opinion: item.opinion,
          personalDescription: item.personalDescription,
        },
      });
    }
  }

  console.log('✅ Seed completado exitosamente.');
}

main()
  .catch((e) => {
    console.error('Error en seed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

