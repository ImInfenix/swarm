import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import { Prisma } from '@prisma/client'
import prisma from '../lib/prisma'

export default function Projects(props: InferGetServerSidePropsType<typeof getServerSideProps>) {

    return (
        <div>
            <h1>Projects</h1>
            <p>
                Here is the list of all projects maintained by swarm.
            </p>

            {props.projects.map(project => {
                return (
                    <div key={project.id}>
                        <h2>{project.name}</h2>
                        <p>Owner is {project.ownerId}</p>
                    </div>
                )
            })}
        </div>
    )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {

    let projects: Prisma.PromiseReturnType<typeof prisma.project.findMany> = await prisma.project.findMany({
        orderBy: { createdAt: 'desc' },
    })

    projects = JSON.parse(JSON.stringify(projects))

    return { props: { projects } }
}