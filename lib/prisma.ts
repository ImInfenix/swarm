import { PrismaClient } from '@prisma/client'

let prismaInstance: PrismaClient

if (process.env.NODE_ENV === 'production') {
  prismaInstance = new PrismaClient()
} else {
  let globalWithPrisma = global as typeof globalThis & {
    prisma: PrismaClient
  }
  if (!globalWithPrisma.prisma) {
    globalWithPrisma.prisma = new PrismaClient()
  }
  prismaInstance = globalWithPrisma.prisma
}

export default prismaInstance
