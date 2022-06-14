import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import { Prisma } from '@prisma/client'
import prisma from '../lib/prisma'
import ProjectSummaryCard from '../components/projects/ProjectSummaryCard'

export default function Projects(
  props: InferGetServerSidePropsType<typeof getServerSideProps>
) {
  return (
    <div>
      <h1>Projects</h1>
      <p>Here is the list of all projects maintained by swarm.</p>

      {props.projects.map((project, key) => {
        return (
          <ProjectSummaryCard
            key={key}
            name={project.name}
            description={project.description}
          />
        )
      })}
    </div>
  )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  let projects: Prisma.PromiseReturnType<typeof prisma.project.findMany> =
    await prisma.project.findMany({
      orderBy: { createdAt: 'desc' },
    })

  projects = JSON.parse(JSON.stringify(projects))

  return { props: { projects } }
}
