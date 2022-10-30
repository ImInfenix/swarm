/* eslint-disable no-console */

const { PrismaClient } = require('@prisma/client')

const prisma = new PrismaClient()

const Users = require('./data/users')
const Projects = require('./data/projects')

async function runSeeders() {
  // Users
  await Promise.all(
    Users.map(async (user) =>
      prisma.user.upsert({
        where: { id: user.id },
        update: {},
        create: user,
      })
    )
  )

  // Posts
  await Promise.all(
    Projects.map(async (project) =>
      prisma.post.upsert({
        where: { id: project.id },
        update: {},
        create: project,
      })
    )
  )
}

runSeeders()
  .catch((e) => {
    console.error(`There was an error while seeding: ${e}`)
    process.exit(1)
  })
  .finally(async () => {
    console.log('Successfully seeded database. Closing connection.')
    await prisma.$disconnect()
  })
