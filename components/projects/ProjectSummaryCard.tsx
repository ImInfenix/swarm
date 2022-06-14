import Link from 'next/link'
import styles from './ProjectSummaryCard.module.css'

export default function ProjectSummaryCard(props: {
  name: string
  description: string | null
}) {
  return (
    <div className={styles.projectSummaryCard}>
      <Link href={`/projects/${props.name}`}>
        <a>
          <h3>{props.name}</h3>
          <p>{props.description ? props.description : null}</p>
        </a>
      </Link>
    </div>
  )
}
