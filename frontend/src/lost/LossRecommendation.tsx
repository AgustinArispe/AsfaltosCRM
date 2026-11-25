import { LOSS_REASON_LABELS } from '../pipeline/config'
import type { LossReason } from '../pipeline/types'
import { CommercialRecommendation } from '../shared/CommercialRecommendation'

const LOSS_RECOMMENDATIONS: Record<LossReason, string> = {
  SIN_RESPUESTA:
    'No dejes la venta sin seguimiento. Si el cliente no responde, retomá el contacto a tiempo.',
  PRECIO:
    'Confirmá el presupuesto antes de cotizar. Si la propuesta queda fuera de alcance, ofrecé una alternativa concreta.',
  COMPETENCIA:
    'Averiguá qué definió la elección del cliente y reforzá ese punto en la próxima propuesta.',
  PROYECTO_CANCELADO:
    'Confirmá que la obra sigue en pie antes de cotizar. Si se cancela, registrá el motivo.',
  OTRO: 'Registrá el motivo concreto de cada pérdida. Usá ese detalle para corregir lo que se repite.',
}

export function LossRecommendation({
  reasons,
}: {
  reasons: ReadonlyArray<{ key: LossReason; value: number }>
}) {
  const [first, second] = [...reasons].sort((left, right) => right.value - left.value)
  if (!first || first.value <= 0) return null

  return (
    <CommercialRecommendation title='Qué mejorar'>
      {first.value === second?.value ? (
        'Revisá los cierres y definí qué ajuste vas a aplicar en el próximo seguimiento.'
      ) : (
        <>
          <strong>{LOSS_REASON_LABELS[first.key]}</strong> · {LOSS_RECOMMENDATIONS[first.key]}
        </>
      )}
    </CommercialRecommendation>
  )
}
