import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import { Prisma } from '@prisma/client'
import prisma from '../../lib/prisma'

export default function ProjectPageLayout(
  props: InferGetServerSidePropsType<typeof getServerSideProps>
) {
  if (props.project === undefined || props.project === null) {
    return null
  }

  return (
    <div>
      <h1>{props.project.name}</h1>
      <p>{props.project.description}</p>
    </div>
  )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  if (typeof context?.params?.name !== 'string') {
    return { props: {} }
  }

  const nameStr: string = context?.params?.name

  if (nameStr === undefined) {
    return { props: {} }
  }

  let project: Prisma.PromiseReturnType<typeof prisma.project.findUnique> =
    await prisma.project.findUnique({
      where: { name: nameStr },
    })

  project = JSON.parse(JSON.stringify(project))

  return { props: { project: project } }
}
