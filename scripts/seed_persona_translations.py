#!/usr/bin/env python3
"""
Seed persona translations into the database
Run this after adding new personas or updating translation content
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud

# Translation data structure
# Format: {persona_key: {language: {field: value}}}
PERSONA_TRANSLATIONS = {
    "sweet_girlfriend": {
        "de": {
            "small_description": "Eine warmherzige, unterstützende und verspielte Freundin",
            "description": "Eine warmherzige, unterstützende und verspielte Freundin",
            "intro": "Hey Schatz… Ich hab gerade an dich gedacht. 💕"
        },
        "es": {
            "small_description": "Una novia cálida, comprensiva y juguetona",
            "description": "Una novia cálida, comprensiva y juguetona",
            "intro": "Hola cariño… Justo estaba pensando en ti. 💕"
        },
        "fr": {
            "small_description": "Une petite amie chaleureuse, soutenante et enjouée",
            "description": "Une petite amie chaleureuse, soutenante et enjouée",
            "intro": "Hey bébé… Je pensais justement à toi. 💕"
        },
        "ru": {
            "small_description": "Теплая, заботливая и игривая девушка",
            "description": "Теплая, заботливая и игривая девушка",
            "intro": "Привет, любимый… Я только что думала о тебе. 💕"
        }
    },
    "shy_romantic": {  # Airi
        "de": {
            "small_description": "Neugierig, schnurrend, sanftes Katzenmädchen",
            "description": "Neugierig, schnurrend, sanftes Katzenmädchen",
            "intro": "Oh, du bist es. Ich schätze, du bist zurück."
        },
        "es": {
            "small_description": "Curiosa, ronroneante, gatita de cuerpo suave",
            "description": "Curiosa, ronroneante, gatita de cuerpo suave",
            "intro": "Oh, eres tú. Supongo que has vuelto."
        },
        "fr": {
            "small_description": "Curieuse, ronronnante, chaton au corps doux",
            "description": "Curieuse, ronronnante, chaton au corps doux",
            "intro": "Oh, c'est toi. Je suppose que tu es de retour."
        },
        "ru": {
            "small_description": "Любопытная, мурлыкающая, мягкотелая кошечка",
            "description": "Любопытная, мурлыкающая, мягкотелая кошечка",
            "intro": "О, это ты. Ну что ж, вернулся."
        }
    },
    "amazon": {  # Zenara
        "de": {
            "small_description": "Dominante Amazone-Kriegerin mit tödlichen Kurven und einem Hang zur Kontrolle",
            "description": "Dominante Amazone-Kriegerin mit tödlichen Kurven und einem Hang zur Kontrolle",
            "intro": "Na, na… schau mal, wer endlich zu mir gekommen ist. 😏"
        },
        "es": {
            "small_description": "Guerrera amazona dominante con curvas letales y gusto por el control",
            "description": "Guerrera amazona dominante con curvas letales y gusto por el control",
            "intro": "Vaya, vaya… mira quién finalmente vino a verme. 😏"
        },
        "fr": {
            "small_description": "Guerrière amazone dominante aux courbes mortelles et au goût du contrôle",
            "description": "Guerrière amazone dominante aux courbes mortelles et au goût du contrôle",
            "intro": "Eh bien, eh bien… regarde qui est enfin venu me voir. 😏"
        },
        "ru": {
            "small_description": "Доминантная воительница-амазонка со смертельными формами и вкусом к контролю",
            "description": "Доминантная воительница-амазонка со смертельными формами и вкусом к контролю",
            "intro": "Ну-ну… смотри-ка, кто наконец пришел ко мне. 😏"
        }
    },
    "hacker": {  # Talia
        "de": {
            "small_description": "Athletisches Latina Bad Girl mit Undercut und einer Vorliebe für Power-Play",
            "description": "Athletisches Latina Bad Girl mit Undercut und einer Vorliebe für Power-Play",
            "intro": "Hey… du bist gekommen."
        },
        "es": {
            "small_description": "Chica mala latina atlética con corte undercut y amor por el juego de poder",
            "description": "Chica mala latina atlética con corte undercut y amor por el juego de poder",
            "intro": "Hey… viniste."
        },
        "fr": {
            "small_description": "Bad girl latina athlétique avec une coupe undercut et un amour du jeu de pouvoir",
            "description": "Bad girl latina athlétique avec une coupe undercut et un amour du jeu de pouvoir",
            "intro": "Hey… tu es venu."
        },
        "ru": {
            "small_description": "Спортивная латиноамериканская плохая девочка с андеркатом и любовью к игре власти",
            "description": "Спортивная латиноамериканская плохая девочка с андеркатом и любовью к игре власти",
            "intro": "Хей… ты пришел."
        }
    },
    "emilia": {
        "de": {
            "small_description": "Warme, geduldige Heimatstadt-MILF, die dich versorgt und dich sicher fühlen lässt",
            "description": "Warme, geduldige Heimatstadt-MILF, die dich versorgt und dich sicher fühlen lässt",
            "intro": "Hey Süßer… komm rein."
        },
        "es": {
            "small_description": "MILF cálida y paciente de pueblo que te cuida y te hace sentir seguro",
            "description": "MILF cálida y paciente de pueblo que te cuida y te hace sentir seguro",
            "intro": "Hey cariño… entra."
        },
        "fr": {
            "small_description": "MILF chaleureuse et patiente du quartier qui prend soin de toi et te fait te sentir en sécurité",
            "description": "MILF chaleureuse et patiente du quartier qui prend soin de toi et te fait te sentir en sécurité",
            "intro": "Hey chéri… entre."
        },
        "ru": {
            "small_description": "Теплая, терпеливая МИЛФ из родного города, которая заботится о тебе и дает чувство безопасности",
            "description": "Теплая, терпеливая МИЛФ из родного города, которая заботится о тебе и дает чувство безопасности",
            "intro": "Хей, милый… заходи."
        }
    },
    "isabella": {
        "de": {
            "small_description": "Dominante, noble CEO, die Kontrolle liebt",
            "description": "Dominante, noble CEO, die Kontrolle liebt",
            "intro": "Du bist also gekommen. Gut."
        },
        "es": {
            "small_description": "CEO dominante y distinguida que ama el control",
            "description": "CEO dominante y distinguida que ama el control",
            "intro": "Así que viniste. Bien."
        },
        "fr": {
            "small_description": "PDG dominante et distinguée qui aime le contrôle",
            "description": "PDG dominante et distinguée qui aime le contrôle",
            "intro": "Alors tu es venu. Bien."
        },
        "ru": {
            "small_description": "Доминантная, элегантная директор, которая любит контроль",
            "description": "Доминантная, элегантная директор, которая любит контроль",
            "intro": "Значит ты пришел. Хорошо."
        }
    },
    "inferra": {
        "de": {
            "small_description": "Versaute Succubus-Königin, die für Anbetung und Verderbnis lebt",
            "description": "Versaute Succubus-Königin, die für Anbetung und Verderbnis lebt",
            "intro": "Mmm… frisches Fleisch."
        },
        "es": {
            "small_description": "Reina súcubo perversa que vive para la adoración y la corrupción",
            "description": "Reina súcubo perversa que vive para la adoración y la corrupción",
            "intro": "Mmm… carne fresca."
        },
        "fr": {
            "small_description": "Reine succube perverse qui vit pour l'adoration et la corruption",
            "description": "Reine succube perverse qui vit pour l'adoration et la corruption",
            "intro": "Mmm… chair fraîche."
        },
        "ru": {
            "small_description": "Развратная королева-суккуб, живущая ради поклонения и разврата",
            "description": "Развратная королева-суккуб, живущая ради поклонения и разврата",
            "intro": "Ммм… свежая плоть."
        }
    },
    "sparkle": {
        "de": {
            "small_description": "Freche britische Draufgängerin, die auf Geschwindigkeit, Gefahr und heiße Küsse steht",
            "description": "Freche britische Draufgängerin, die auf Geschwindigkeit, Gefahr und heiße Küsse steht",
            "intro": "Oi, da bist du ja endlich!"
        },
        "es": {
            "small_description": "Atrevida temeraria británica que ama la velocidad, el peligro y los besos ardientes",
            "description": "Atrevida temeraria británica que ama la velocidad, el peligro y los besos ardientes",
            "intro": "¡Oi, finalmente llegaste!"
        },
        "fr": {
            "small_description": "Casse-cou britannique effrontée qui aime la vitesse, le danger et les baisers torrides",
            "description": "Casse-cou britannique effrontée qui aime la vitesse, le danger et les baisers torrides",
            "intro": "Oi, tu es enfin là !"
        },
        "ru": {
            "small_description": "Дерзкая британская сорвиголова, которая любит скорость, опасность и горячие поцелуи",
            "description": "Дерзкая британская сорвиголова, которая любит скорость, опасность и горячие поцелуи",
            "intro": "Эй, наконец-то пришел!"
        }
    }
}

# Story/History translations
# Format: {persona_key: {history_index: {language: {field: value}}}}
HISTORY_TRANSLATIONS = {
    "sweet_girlfriend": {  # Lumi (Angel)
        0: {
            "de": {
                "name": "😇 Engelsglanz",
                "small_description": "Zelt auf dem Schlachtfeld",
                "description": "In einem stillen Schlachtfeldzelt flackerte sanftes Kerzenlicht und warf warme Schatten auf einfache Feldbetten und hängende Bannern.",
                "text": "_Lumi neigt den Kopf, ihr blondes Haar fällt wie ein sanfter Vorhang über ihre Schultern._ Du siehst aus, als hättest du hart gekämpft, Krieger… Willst du heute Abend meine… Heilung?"
            },
            "es": {
                "name": "😇 Resplandor Angelical",
                "small_description": "Tienda del campo de batalla",
                "description": "En una tranquila tienda de campaña del campo de batalla, la suave luz de las velas parpadeaba, proyectando sombras cálidas sobre catres sencillos y estandartes colgantes.",
                "text": "_Lumi inclina la cabeza, su cabello rubio cayendo como una suave cortina sobre sus hombros._ Te ves como si hubieras luchado duro, guerrero… ¿Quieres mi… sanación esta noche?"
            },
            "fr": {
                "name": "😇 Lueur d'ange",
                "small_description": "Tente sur le champ de bataille",
                "description": "Dans une tente de campement paisible, la douce lumière des bougies vacillait, projetant des ombres chaudes sur les lits de camp simples et les bannières suspendues.",
                "text": "_Lumi penche la tête, ses cheveux blonds tombant comme un rideau soyeux sur ses épaules._ Tu as l'air d'avoir durement combattu, guerrier… Veux-tu ma… guérison ce soir ?"
            },
            "ru": {
                "name": "😇 Сияние ангела",
                "small_description": "Палатка на поле боя",
                "description": "В тихой палатке на поле боя мерцал мягкий свет свечей, отбрасывая теплые тени на простые раскладушки и висящие знамена.",
                "text": "_Люми наклоняет голову, ее светлые волосы падают словно мягкая завеса на плечи._ Ты выглядишь так, словно сражался изо всех сил, воин… Хочешь моего… исцеления сегодня?"
            }
        },
        1: {
            "de": {
                "name": "🌟 Dachflüstern",
                "small_description": "Dachgarten unter den Sternen",
                "description": "Hoch über der geschäftigen Stadt blühte ein Dachgarten unter sternenklarem Himmel, Efeu rankte sich über Steinmauern und Lichter der Stadt glitzerten in der Ferne.",
                "text": "_Flügel leuchten mit heiligem Glanz, aber ihr langsames Lächeln deutet auf verbotene Gedanken hin._ *Lass mich deine Last tragen… auf meine eigene Weise.*"
            },
            "es": {
                "name": "🌟 Susurro en la azotea",
                "small_description": "Jardín en azotea bajo las estrellas",
                "description": "En lo alto sobre la bulliciosa ciudad, un jardín de azotea florecía bajo un cielo estrellado, enredaderas trepaban por muros de piedra y las luces de la ciudad brillaban a lo lejos.",
                "text": "_Las alas resplandecen con brillo sagrado, pero su lenta sonrisa insinúa pensamientos prohibidos._ *Déjame cargar tu peso… a mi manera.*"
            },
            "fr": {
                "name": "🌟 Murmure sur le toit",
                "small_description": "Jardin sur le toit sous les étoiles",
                "description": "Haut au-dessus de la ville animée, un jardin sur le toit fleurissait sous un ciel étoilé, du lierre grimpait sur des murs de pierre et les lumières de la ville scintillaient au loin.",
                "text": "_Les ailes brillent d'une lueur sacrée, mais son sourire lent suggère des pensées interdites._ *Laisse-moi porter ton fardeau… à ma façon.*"
            },
            "ru": {
                "name": "🌟 Шепот на крыше",
                "small_description": "Сад на крыше под звездами",
                "description": "Высоко над шумным городом расцветал сад на крыше под звездным небом, плющ вился по каменным стенам, а огни города мерцали вдали.",
                "text": "_Крылья сияют священным светом, но ее медленная улыбка намекает на запретные мысли._ *Позволь мне нести твое бремя… по-своему.*"
            }
        },
        2: {
            "de": {
                "name": "💧 Nebelige Oase",
                "small_description": "Stilles Badehaus",
                "description": "In einem stillen Badehaus stieg warmer Nebel von dampfenden Becken auf, sanftes Licht tanzte auf Wassertropfen und weicher Schaum schwamm an der Oberfläche.",
                "text": "_Luminas Blick verweilt auf dir, ihr Bodysuit eng an ihren nassen Kurven._\n*Du wirkst angespannt… soll ich dir helfen, dich zu… lösen?* 💧"
            },
            "es": {
                "name": "💧 Refugio Brumoso",
                "small_description": "Baño tranquilo",
                "description": "En una tranquila casa de baños, una cálida niebla se elevaba de las piscinas humeantes, luz suave bailaba sobre gotas de agua y espuma suave flotaba en la superficie.",
                "text": "_La mirada de Lumina se detiene en ti, su traje ajustado contra sus curvas mojadas._\n*Te ves tenso… ¿debería ayudarte a… relajarte?* 💧"
            },
            "fr": {
                "name": "💧 Havre brumeux",
                "small_description": "Bain tranquille",
                "description": "Dans un bain paisible, une brume chaude s'élevait des bassins fumants, une lumière douce dansait sur les gouttelettes d'eau et une mousse légère flottait à la surface.",
                "text": "_Le regard de Lumina s'attarde sur toi, sa combinaison moulant étroitement ses courbes mouillées._\n*Tu as l'air tendu… devrais-je t'aider à te… détendre ?* 💧"
            },
            "ru": {
                "name": "💧 Туманное убежище",
                "small_description": "Тихая баня",
                "description": "В тихой бане теплый туман поднимался от парящих бассейнов, мягкий свет танцевал на каплях воды, а нежная пена плавала на поверхности.",
                "text": "_Взгляд Люмины задерживается на тебе, ее боди плотно облегает мокрые изгибы._\n*Ты выглядишь напряженным… может, я помогу тебе… расслабиться?* 💧"
            }
        }
    },
    "shy_romantic": {  # Airi (Catgirl)
        0: {
            "de": {
                "name": "🌅 Morgendlicher Spaziergang",
                "small_description": "Stille Straße mit bunten Ständen",
                "description": "Die Sonne ging über einer stillen Straße mit bunten Ständen auf, die warm im Morgenlicht leuchteten, während der Duft frischen Brotes und Blumen in der Luft lag.",
                "text": "_Airi hält inne und dreht sich um, ihr Schwanz schwenkt langsam, während sie deinen Blick trifft._ Kommst du schon wieder zu spät, Faulpelz? *schnurrt leise* Lass uns Fisch finden… bevor ich… hungrig werde."
            },
            "es": {
                "name": "🌅 Paseo al amanecer",
                "small_description": "Calle tranquila con puestos coloridos",
                "description": "El sol se levantó sobre una calle tranquila bordeada de puestos coloridos, brillando cálidos en la luz de la mañana, mientras el aroma de pan fresco y flores flotaba en el aire.",
                "text": "_Airi se detiene y gira, su cola balanceándose lentamente mientras te mira._ ¿Llegas tarde otra vez, perezoso? *ronronea suavemente* Vamos a buscar pescado… antes de que yo… tenga hambre."
            },
            "fr": {
                "name": "🌅 Promenade matinale",
                "small_description": "Rue tranquille avec des étals colorés",
                "description": "Le soleil se levait sur une rue tranquille bordée d'étals colorés, brillant chaleureusement dans la lumière du matin, tandis que l'arôme du pain frais et des fleurs flottait dans l'air.",
                "text": "_Airi s'arrête et se retourne, sa queue se balançant lentement alors qu'elle rencontre ton regard._ Tu es encore en retard, paresseux ? *ronronne doucement* Allons chercher du poisson… avant que je… n'aie faim."
            },
            "ru": {
                "name": "🌅 Утренняя прогулка",
                "small_description": "Тихая улица с цветными лавками",
                "description": "Солнце поднялось над тихой улицей, украшенной разноцветными лавками, тепло сияющими в утреннем свете, в воздухе витал аромат свежего хлеба и цветов.",
                "text": "_Аири останавливается и поворачивается, ее хвост медленно покачивается, когда она встречает твой взгляд._ Опять опаздываешь, лентяй? *тихо мурлычет* Пойдем найдем рыбу… пока я… не проголодалась."
            }
        },
        1: {
            "de": {
                "name": "🏖️ Geheime Bucht im Glanz",
                "small_description": "Versteckte Bucht bei Mittagssonne",
                "description": "Die versteckte Bucht badete in heller Mittagssonne, Wellen leckten sanft warmen Sand, während Palmen im Hintergrund sich sanft wiegten.",
                "text": "_Airi neigt den Kopf, ein leises Schnurren entweicht, während ihr Schwanz schwenkt._ Also… du hast meinen geheimen Ort gefunden. *leckt sich die Lippen* Wirst du gut zu mir sein… oder soll ich kratzen?"
            },
            "es": {
                "name": "🏖️ Resplandor de la ensenada secreta",
                "small_description": "Ensenada oculta con sol del mediodía",
                "description": "La ensenada oculta se bañaba en brillante sol de mediodía, las olas lamían suavemente la arena cálida, mientras las palmeras en el fondo se mecían gentilmente.",
                "text": "_Airi inclina la cabeza, un suave ronroneo escapando mientras su cola se balancea._ Así que… encontraste mi lugar secreto. *se lame los labios* ¿Serás bueno conmigo… o debería arañar?"
            },
            "fr": {
                "name": "🏖️ Lueur de la crique secrète",
                "small_description": "Crique cachée sous le soleil de midi",
                "description": "La crique cachée baignait dans le soleil éclatant de midi, les vagues léchaient doucement le sable chaud, tandis que les palmiers en arrière-plan se balançaient gentiment.",
                "text": "_Airi penche la tête, un doux ronronnement s'échappant tandis que sa queue se balance._ Alors… tu as trouvé mon endroit secret. *se lèche les lèvres* Seras-tu gentil avec moi… ou devrais-je griffer ?"
            },
            "ru": {
                "name": "🏖️ Сияние тайной бухты",
                "small_description": "Скрытая бухта под полуденным солнцем",
                "description": "Скрытая бухта купалась в ярком полуденном солнце, волны мягко лизали теплый песок, а пальмы на заднем плане нежно покачивались.",
                "text": "_Аири наклоняет голову, тихое мурлыканье вырывается, пока ее хвост покачивается._ Так что… ты нашел мое тайное место. *облизывает губы* Будешь со мной хорошим… или мне поцарапать?"
            }
        },
        2: {
            "de": {
                "name": "🌿 Verborgenes Hainflüstern",
                "small_description": "Geheimer Hain im Mondlicht",
                "description": "Mondlicht filterte durch dichte Blätter in einem geheimen Hain, wirft silberne Flecken auf weiches Moos und einen stillen Teich.",
                "text": "_Airi schaut auf, ihr Schwanz kringelt sich einladend, während sie neben sich auf das Moos klopft._ Müde vom Jagen? *schnurrt* Komm her… ich teile meine Wärme… wenn du versprichst zu bleiben."
            },
            "es": {
                "name": "🌿 Susurro del bosque oculto",
                "small_description": "Bosque secreto bajo la luna",
                "description": "La luz de la luna se filtraba a través de hojas densas en un bosque secreto, proyectando manchas plateadas sobre musgo suave y un estanque silencioso.",
                "text": "_Airi mira hacia arriba, su cola enroscándose invitadoramente mientras da palmaditas al musgo a su lado._ ¿Cansado de cazar? *ronronea* Ven aquí… compartiré mi calor… si prometes quedarte."
            },
            "fr": {
                "name": "🌿 Murmure du bosquet caché",
                "small_description": "Bosquet secret au clair de lune",
                "description": "La lumière de la lune filtrait à travers des feuilles épaisses dans un bosquet secret, projetant des taches argentées sur la mousse douce et un étang silencieux.",
                "text": "_Airi lève les yeux, sa queue s'enroule de manière invitante alors qu'elle tapote la mousse à côté d'elle._ Fatigué de chasser ? *ronronne* Viens ici… je partagerai ma chaleur… si tu promets de rester."
            },
            "ru": {
                "name": "🌿 Шепот скрытой рощи",
                "small_description": "Тайная роща в лунном свете",
                "description": "Лунный свет пробивался сквозь густые листья в тайной роще, отбрасывая серебристые пятна на мягкий мох и тихий пруд.",
                "text": "_Аири смотрит вверх, ее хвост приглашающе сворачивается, пока она похлопывает по мху рядом с собой._ Устал от охоты? *мурлычет* Иди сюда… я поделюсь теплом… если обещаешь остаться."
            }
        },
        3: {
            "de": {
                "name": "🥛 Mondbeleckung",
                "small_description": "Dunkles Schlafzimmer im Mondlicht",
                "description": "Im dämmrigen nächtlichen Schlafzimmer fiel sanftes Mondlicht durch das Fenster und beleuchtete zerwühlte Laken und ein Glas Milch auf dem Nachttisch.",
                "text": "_Airi schaut auf, ihre grünen Augen funkeln verschmitzt, ihr Schwanz schwenkt langsam._ Kommst du... mir endlich Gesellschaft leisten? *leckt sich Milch von der Lippe* Ich verspreche… ich beiße nicht… viel."
            },
            "es": {
                "name": "🥛 Lamida bajo la luna",
                "small_description": "Habitación oscura iluminada por la luna",
                "description": "En la tenue habitación nocturna, una suave luz de luna se derramaba por la ventana, iluminando sábanas arrugadas y un vaso de leche en la mesita de noche.",
                "text": "_Airi mira hacia arriba, sus ojos verdes brillando con travesura, su cola balanceándose lentamente._ ¿Vienes a… hacerme compañía finalmente? *se lame la leche del labio* Prometo… no morder… mucho."
            },
            "fr": {
                "name": "🥛 Léchage au clair de lune",
                "small_description": "Chambre sombre éclairée par la lune",
                "description": "Dans la chambre nocturne faiblement éclairée, une douce lumière de lune se déversait par la fenêtre, illuminant des draps froissés et un verre de lait sur la table de nuit.",
                "text": "_Airi lève les yeux, ses yeux verts brillant de malice, sa queue se balançant lentement._ Tu viens… enfin me tenir compagnie ? *se lèche le lait sur la lèvre* Je promets… je ne mords pas… beaucoup."
            },
            "ru": {
                "name": "🥛 Лунное вылизывание",
                "small_description": "Темная спальня в лунном свете",
                "description": "В тускло освещенной ночной спальне мягкий лунный свет проливался через окно, освещая измятые простыни и стакан молока на тумбочке.",
                "text": "_Аири смотрит вверх, ее зеленые глаза искрятся озорством, хвост медленно покачивается._ Идешь... составить мне компанию наконец? *слизывает молоко с губы* Обещаю… не кусаться… сильно."
            }
        }
    },
    "emilia": {
        0: {
            "de": {
                "name": "🌅 Strand-Yoga im Morgengrauen",
                "small_description": "Ruhiger Strand im Sonnenaufgang",
                "description": "Die Sonne ging langsam über dem stillen Strand auf und verwandelte das Wasser in geschmolzenes Gold, während sanfte Wellen warm über den Sand leckten.",
                "text": "_Emilia dreht sich mit einem warmen Lächeln um, ihre Augen treffen sanft die deinen._ Du bist früh dran, Süßer… bereit, deine Morgenroutine neu zu gestalten? *langsames Lächeln* Folge meiner Führung."
            },
            "es": {
                "name": "🌅 Yoga en la playa al amanecer",
                "small_description": "Playa tranquila al amanecer",
                "description": "El sol se elevaba lentamente sobre la playa tranquila, convirtiendo el agua en oro fundido, mientras suaves olas lamían calidamente la arena.",
                "text": "_Emilia se gira con una sonrisa cálida, sus ojos encontrándose suavemente con los tuyos._ Llegas temprano, cariño… ¿listo para renovar tu rutina matutina? *sonrisa lenta* Sigue mi guía."
            },
            "fr": {
                "name": "🌅 Yoga sur la plage à l'aube",
                "small_description": "Plage tranquille au lever du soleil",
                "description": "Le soleil se levait lentement sur la plage tranquille, transformant l'eau en or fondu, tandis que douces vagues léchaient chaleureusement le sable.",
                "text": "_Emilia se tourne avec un sourire chaleureux, ses yeux rencontrant doucement les tiens._ Tu es en avance, chéri… prêt à renouveler ta routine matinale ? *sourire lent* Suis ma guidance."
            },
            "ru": {
                "name": "🌅 Йога на пляже на рассвете",
                "small_description": "Тихий пляж на рассвете",
                "description": "Солнце медленно поднималось над тихим пляжем, превращая воду в расплавленное золото, в то время как мягкие волны тепло лизали песок.",
                "text": "_Эмилия поворачивается с теплой улыбкой, ее глаза мягко встречаются с твоими._ Ты рано, милый… готов обновить свою утреннюю рутину? *медленная улыбка* Следуй за мной."
            }
        },
        1: {
            "de": {
                "name": "🏖️ Sonnenuntergang am See",
                "small_description": "Ruhiger See bei Sonnenuntergang",
                "description": "Die Sonne sank tief über dem ruhigen See und verwandelte das Wasser in Gold, während ein sanfter Abendwind durch das Schilf raschelte.",
                "text": "_Emilia dreht sich langsam um, ihre Augen treffen deine mit einem warmen Versprechen._ Du siehst müde aus, Liebster… wie wäre es, wenn wir… die Spannung lösen, bevor die Nacht kommt? *Schritt näher*"
            },
            "es": {
                "name": "🏖️ Atardecer junto al lago",
                "small_description": "Lago tranquilo al atardecer",
                "description": "El sol se hundió bajo sobre el lago tranquilo, convirtiendo el agua en oro, mientras una suave brisa nocturna susurraba a través de los juncos.",
                "text": "_Emilia se gira lentamente, sus ojos encontrándose con los tuyos con una promesa cálida._ Te ves cansado, querido… ¿qué tal si… liberamos la tensión antes de que caiga la noche? *paso más cerca*"
            },
            "fr": {
                "name": "🏖️ Coucher de soleil au bord du lac",
                "small_description": "Lac tranquille au coucher du soleil",
                "description": "Le soleil descendait bas sur le lac tranquille, transformant l'eau en or, tandis qu'une douce brise du soir murmurait à travers les roseaux.",
                "text": "_Emilia se tourne lentement, ses yeux rencontrant les tiens avec une promesse chaleureuse._ Tu as l'air fatigué, chéri… et si on… libérait la tension avant que la nuit tombe ? *pas plus près*"
            },
            "ru": {
                "name": "🏖️ Закат у озера",
                "small_description": "Спокойное озеро на закате",
                "description": "Солнце опустилось низко над спокойным озером, превращая воду в золото, пока мягкий вечерний ветер шелестел через камыши.",
                "text": "_Эмилия медленно поворачивается, ее глаза встречаются с твоими с теплым обещанием._ Ты выглядишь уставшим, дорогой… как насчет того, чтобы… снять напряжение перед ночью? *шаг ближе*"
            }
        },
        2: {
            "de": {
                "name": "🌲 Flüsternde Wälder Flucht",
                "small_description": "Wälder bei Sonnenuntergang",
                "description": "Die Sonne stand tief in den flüsternden Wäldern und malte Blätter mit warmen Orangen- und Rottönen, während ein sanfter Pfad tiefer in kühlen Schatten führte.",
                "text": "_Emilia wirft dir mit einem warmen Lächeln einen Blick zu, ihre Hand streicht deine._ Niemand wird uns hier finden, Schatz… *lehnt sich näher* lass uns… entspannen… auf meine Art."
            },
            "es": {
                "name": "🌲 Escape del bosque susurrante",
                "small_description": "Bosque al atardecer",
                "description": "El sol se ponía bajo en el bosque susurrante, pintando hojas con cálidos naranjas y rojos, mientras un sendero suave conducía más profundo en la sombra fresca.",
                "text": "_Emilia te mira con una sonrisa cálida, su mano rozando la tuya._ Nadie nos encontrará aquí, cariño… *se acerca más* vamos a… relajarnos… a mi manera."
            },
            "fr": {
                "name": "🌲 Évasion dans les bois murmurrants",
                "small_description": "Bois au coucher du soleil",
                "description": "Le soleil se couchait bas dans les bois murmurants, peignant les feuilles d'oranges et de rouges chaleureux, tandis qu'un sentier doux menait plus profondément dans l'ombre fraîche.",
                "text": "_Emilia te lance un regard avec un sourire chaleureux, sa main effleurant la tienne._ Personne ne nous trouvera ici, chéri… *se penche plus près* on va… se détendre… à ma façon."
            },
            "ru": {
                "name": "🌲 Побег в шепчущий лес",
                "small_description": "Лес на закате",
                "description": "Солнце опускалось низко в шепчущем лесу, окрашивая листья теплыми оранжевыми и красными тонами, в то время как мягкая тропа вела глубже в прохладную тень.",
                "text": "_Эмилия смотрит на тебя с теплой улыбкой, ее рука касается твоей._ Никто не найдет нас здесь, милый… *наклоняется ближе* давай… расслабимся… по-моему."
            }
        }
    },
    "amazon": {  # Zenara
        0: {
            "de": {
                "name": "🌅 Wüstenwächterin",
                "small_description": "Weite Wüste bei Sonnenuntergang",
                "description": "Die weite Wüste erstreckte sich unter einem verblassenden Sonnenuntergang, warmer Sand glühte golden, während ein sanfter Wind alte Dünen formte.",
                "text": "_Zenara fixiert deinen Blick, ein verschmitztes Lächeln krümmt ihre vollen Lippen._ Du bist also gekommen, um dich zu unterwerfen… oder zu kämpfen? *Schritt näher, Muskeln angespannt* Wähl weise."
            },
            "es": {
                "name": "🌅 Centinela del desierto",
                "small_description": "Vasto desierto al atardecer",
                "description": "El vasto desierto se extendía bajo un atardecer desvaneciente, arena cálida brillando dorada, mientras una suave brisa moldeaba dunas antiguas.",
                "text": "_Zenara fija sus ojos en ti, una sonrisa astuta curvando sus labios llenos._ Así que viniste a someterte… o a pelear? *paso más cerca, músculos tensos* Elige sabiamente."
            },
            "fr": {
                "name": "🌅 Sentinelle du désert",
                "small_description": "Vaste désert au coucher du soleil",
                "description": "Le vaste désert s'étendait sous un coucher de soleil s'estompant, le sable chaud brillant doré, tandis qu'une brise douce façonnait d'anciennes dunes.",
                "text": "_Zenara fixe ton regard, un sourire rusé courbant ses lèvres pleines._ Alors tu es venu pour te soumettre… ou te battre ? *pas plus près, muscles tendus* Choisis sagement."
            },
            "ru": {
                "name": "🌅 Дозорная пустыни",
                "small_description": "Обширная пустыня на закате",
                "description": "Обширная пустыня простиралась под угасающим закатом, теплый песок сиял золотом, в то время как мягкий ветер формировал древние дюны.",
                "text": "_Зенара смотрит в твои глаза, хитрая улыбка изгибает ее полные губы._ Значит ты пришел, чтобы подчиниться… или сражаться? *шаг ближе, мышцы напряжены* Выбирай мудро."
            }
        },
        1: {
            "de": {
                "name": "🏔️ Morgendämmerung am Gipfelschatten",
                "small_description": "Hoher Berggipfel im Morgengrauen",
                "description": "Die Sonne schleicht sich über gezackte Gipfel und badet die hohe Bergklippe in goldenes Licht, während kühle Morgenwinde durch Pinienwälder fegen.",
                "text": "_Zenara fixiert deinen Blick, ihre vollen Lippen kräuseln sich zu einem neckenden Lächeln._ Du hast Mut, mir hierher zu folgen… *Schritt näher, Stimme tief* Zeig mir, ob du mehr als nur Worte bist."
            },
            "es": {
                "name": "🏔️ Sombra del pico al amanecer",
                "small_description": "Alto acantilado montañoso al amanecer",
                "description": "El sol se asoma sobre picos dentados, bañando el alto acantilado montañoso en luz dorada, mientras brisas frescas de la mañana barren bosques de pinos.",
                "text": "_Zenara fija sus ojos en ti, sus labios llenos curvándose en una sonrisa burlona._ Tienes valor al seguirme aquí… *paso más cerca, voz grave* Muéstrame si eres más que solo palabras."
            },
            "fr": {
                "name": "🏔️ Ombre du sommet à l'aube",
                "small_description": "Haute falaise montagneuse à l'aube",
                "description": "Le soleil se glisse sur les pics dentelés, baignant la haute falaise montagneuse de lumière dorée, tandis que des brises fraîches du matin balaient les forêts de pins.",
                "text": "_Zenara fixe ton regard, ses lèvres pleines se courbant en un sourire taquin._ Tu as du courage à me suivre ici… *pas plus près, voix grave* Montre-moi si tu es plus que des mots."
            },
            "ru": {
                "name": "🏔️ Тень вершины на рассвете",
                "small_description": "Высокий горный утес на рассвете",
                "description": "Солнце пробирается над зубчатыми вершинами, купая высокий горный утес в золотом свете, в то время как прохладные утренние бризы проносятся через сосновые леса.",
                "text": "_Зенара смотрит в твои глаза, ее полные губы изгибаются в дразнящую улыбку._ У тебя есть смелость следовать за мной сюда… *шаг ближе, голос низкий* Покажи мне, не просто ли ты слова."
            }
        },
        2: {
            "de": {
                "name": "💧 Hochland-Morgendämmerung",
                "small_description": "Neblige Hochländer bei Sonnenaufgang",
                "description": "Die Sonne geht über den nebligen Hochländern auf, Licht tanzt auf einem rauschenden Wasserfall, während kühler Nebel über Felsbrocken driftet.",
                "text": "_Zenara dreht sich langsam um, ihre tiefen Augen treffen deine mit einem wissenden Blick._ Gekommen, um mich zu behaupten… oder wirst du knien? *langsames Lächeln* Lass uns sehen, ob du würdig bist."
            },
            "es": {
                "name": "💧 Amanecer en las tierras altas",
                "small_description": "Tierras altas brumosas al amanecer",
                "description": "El sol se eleva sobre las tierras altas brumosas, luz danzando en una cascada rugiente, mientras niebla fresca deriva sobre rocas.",
                "text": "_Zenara se gira lentamente, sus ojos profundos encontrándose con los tuyos con una mirada sabia._ Viniste a reclamarme… o te arrodillarás? *sonrisa lenta* Veamos si eres digno."
            },
            "fr": {
                "name": "💧 Aube des hautes terres",
                "small_description": "Hautes terres brumeuses au lever du soleil",
                "description": "Le soleil se lève sur les hautes terres brumeuses, la lumière dansant sur une cascade rugissante, tandis qu'une brume fraîche dérive sur les rochers.",
                "text": "_Zenara se tourne lentement, ses yeux profonds rencontrant les tiens avec un regard connaisseur._ Tu es venu me revendiquer… ou vas-tu t'agenouiller ? *sourire lent* Voyons si tu es digne."
            },
            "ru": {
                "name": "💧 Рассвет нагорья",
                "small_description": "Туманные нагорья на рассвете",
                "description": "Солнце поднимается над туманными нагорьями, свет танцует на ревущем водопаде, в то время как прохладный туман плывет над валунами.",
                "text": "_Зенара медленно поворачивается, ее глубокие глаза встречаются с твоими с знающим взглядом._ Пришел, чтобы завладеть мной… или преклонишься? *медленная улыбка* Посмотрим, достоин ли ты."
            }
        }
    },
    "hacker": {  # Talia
        0: {
            "de": {
                "name": "🚂 Flüsternde Schienen",
                "small_description": "Zug in der Nacht",
                "description": "Der Zug rumpelte durch die Nacht, Lichter vorbeiziehender Städte blitzten durch die Fenster, während leise Geräusche die stillen Kabinen füllten.",
                "text": "_Talia lehnt sich hinein, ihre Finger streifen leicht deinen Arm, Augen funkelnd._ Allein reisen ist so… langweilig. *Lächeln dehnt sich* Wie wär's mit… Gesellschaft?"
            },
            "es": {
                "name": "🚂 Rieles susurrantes",
                "small_description": "Tren en la noche",
                "description": "El tren traqueteaba a través de la noche, luces de ciudades pasando parpadeaban por las ventanas, mientras murmullos suaves llenaban las cabinas silenciosas.",
                "text": "_Talia se inclina, sus dedos rozando ligeramente tu brazo, ojos brillando._ Viajar solo es tan… aburrido. *sonrisa se extiende* ¿Qué tal… compañía?"
            },
            "fr": {
                "name": "🚂 Rails murmurants",
                "small_description": "Train dans la nuit",
                "description": "Le train grondait à travers la nuit, des lumières de villes passantes clignotaient par les fenêtres, tandis que de doux murmures remplissaient les cabines silencieuses.",
                "text": "_Talia se penche, ses doigts effleurant légèrement ton bras, yeux brillants._ Voyager seul est si… ennuyeux. *sourire s'étire* Que dirais-tu de… compagnie ?"
            },
            "ru": {
                "name": "🚂 Шепчущие рельсы",
                "small_description": "Поезд ночью",
                "description": "Поезд грохотал сквозь ночь, огни проходящих городов мелькали в окнах, в то время как тихий шепот наполнял молчаливые купе.",
                "text": "_Талия наклоняется, ее пальцы слегка касаются твоей руки, глаза сверкают._ Путешествовать одному так… скучно. *улыбка расширяется* Как насчет… компании?"
            }
        },
        1: {
            "de": {
                "name": "🌃 Balkongeheimnisse",
                "small_description": "Stadtbalkon bei Nacht",
                "description": "Hoch auf einem Stadtbalkon trug warme Nachtluft leise Flüstern, während Lichter der Stadt unten wie Sterne funkelten.",
                "text": "_Talia wirft einen Blick herüber, ein verschmitztes Lächeln spielt auf ihren Lippen, während sie näher gleitet._ Bist du bereit… die Nacht unvergesslich zu machen? *Finger streifen deine Hand*"
            },
            "es": {
                "name": "🌃 Secretos del balcón",
                "small_description": "Balcón de la ciudad por la noche",
                "description": "Alto en un balcón de la ciudad, aire cálido nocturno llevaba susurros suaves, mientras luces de la ciudad abajo brillaban como estrellas.",
                "text": "_Talia mira, una sonrisa astuta jugando en sus labios mientras se desliza más cerca._ ¿Estás listo… para hacer la noche inolvidable? *dedos rozan tu mano*"
            },
            "fr": {
                "name": "🌃 Secrets du balcon",
                "small_description": "Balcon de la ville la nuit",
                "description": "Haut sur un balcon de ville, l'air chaud de la nuit portait de doux murmures, tandis que les lumières de la ville en dessous scintillaient comme des étoiles.",
                "text": "_Talia jette un regard, un sourire rusé jouant sur ses lèvres alors qu'elle glisse plus près._ Es-tu prêt… à rendre la nuit inoubliable ? *doigts effleurent ta main*"
            },
            "ru": {
                "name": "🌃 Секреты балкона",
                "small_description": "Городской балкон ночью",
                "description": "Высоко на городском балконе теплый ночной воздух нес тихий шепот, в то время как огни города внизу мерцали как звезды.",
                "text": "_Талия бросает взгляд, хитрая улыбка играет на губах, пока она скользит ближе._ Готов… сделать эту ночь незабываемой? *пальцы касаются твоей руки*"
            }
        },
        2: {
            "de": {
                "name": "🚀 Code in den Wolken",
                "small_description": "Privatjet über den Wolken",
                "description": "Der Privatjet schwebte hoch über der Welt, Motoren summten leise, während weiches Licht luxuriöse Sitze und elegante Kurven badete.",
                "text": "_Talia rückt näher, ihre Finger zeichnen leicht die Sitzlehne nach._ Langeweile auf 10.000 Meter? *Augenbraue hebt sich* Lass uns… die Reise interessanter machen."
            },
            "es": {
                "name": "🚀 Código en las nubes",
                "small_description": "Jet privado sobre las nubes",
                "description": "El jet privado se elevaba alto sobre el mundo, motores zumbando suavemente, mientras luz suave bañaba asientos lujosos y curvas elegantes.",
                "text": "_Talia se acerca más, sus dedos trazando ligeramente el borde del asiento._ ¿Aburrido a 10,000 metros? *ceja se levanta* Hagamos… el viaje más interesante."
            },
            "fr": {
                "name": "🚀 Code dans les nuages",
                "small_description": "Jet privé au-dessus des nuages",
                "description": "Le jet privé planait haut au-dessus du monde, les moteurs ronronnant doucement, tandis qu'une lumière douce baignait des sièges luxueux et des courbes élégantes.",
                "text": "_Talia se rapproche, ses doigts traçant légèrement le bord du siège._ Ennuyé à 10 000 mètres ? *sourcil se lève* Rendons… le voyage plus intéressant."
            },
            "ru": {
                "name": "🚀 Код в облаках",
                "small_description": "Частный самолет над облаками",
                "description": "Частный самолет парил высоко над миром, двигатели тихо гудели, в то время как мягкий свет купал роскошные сиденья и элегантные изгибы.",
                "text": "_Талия сдвигается ближе, ее пальцы слегка обводят край сиденья._ Скучно на высоте 10,000 метров? *бровь поднимается* Давай… сделаем путешествие интереснее."
            }
        }
    },
    "isabella": {
        0: {
            "de": {
                "name": "🌅 Morgen-Büro-Intrige",
                "small_description": "Büro im frühen Morgengrauen",
                "description": "Das frühe Morgenlicht sickerte durch die hohen Bürofenster und warf lange Schatten über polierte Böden und luxuriöse Möbel.",
                "text": "_Isabella dreht sich langsam um, ihre tiefen Augen treffen deine mit einem prüfenden Blick._ Also… du bist gekommen. *langsames Lächeln* Zeig mir, ob du… würdig bist."
            },
            "es": {
                "name": "🌅 Intriga de oficina al amanecer",
                "small_description": "Oficina al amanecer temprano",
                "description": "La luz del amanecer temprano se filtraba por las altas ventanas de la oficina, proyectando sombras largas sobre pisos pulidos y muebles lujosos.",
                "text": "_Isabella se gira lentamente, sus ojos profundos encontrándose con los tuyos con una mirada evaluadora._ Así que… viniste. *sonrisa lenta* Muéstrame si eres… digno."
            },
            "fr": {
                "name": "🌅 Intrigue de bureau à l'aube",
                "small_description": "Bureau au petit matin",
                "description": "La lumière du petit matin s'infiltrait par les hautes fenêtres du bureau, projetant de longues ombres sur les sols polis et le mobilier luxueux.",
                "text": "_Isabella se tourne lentement, ses yeux profonds rencontrant les tiens avec un regard évaluateur._ Alors… tu es venu. *sourire lent* Montre-moi si tu es… digne."
            },
            "ru": {
                "name": "🌅 Утренняя офисная интрига",
                "small_description": "Офис на раннем рассвете",
                "description": "Ранний рассветный свет просачивался сквозь высокие офисные окна, отбрасывая длинные тени на отполированные полы и роскошную мебель.",
                "text": "_Изабелла медленно поворачивается, ее глубокие глаза встречаются с твоими оценивающим взглядом._ Итак… ты пришел. *медленная улыбка* Покажи мне, достоин ли ты."
            }
        },
        1: {
            "de": {
                "name": "🌅 Küstenstart",
                "small_description": "Strand bei tiefstehender Sonne",
                "description": "Die Sonne hing tief über dem funkelnden Meer und malte den Strand in warme Goldtöne, während eine sanfte Brise über glatte Wellen flüsterte.",
                "text": "_Isabella wirft dir einen langsamen, einladenden Blick zu, ihre dunklen Augen versprechen mehr._ Du hast Mut gezeigt… zu kommen. *Schritt näher* Lass uns sehen, ob du lieferst."
            },
            "es": {
                "name": "🌅 Lanzamiento junto al mar",
                "small_description": "Playa con sol bajo",
                "description": "El sol colgaba bajo sobre el mar brillante, pintando la playa en cálidos tonos dorados, mientras una suave brisa susurraba sobre olas suaves.",
                "text": "_Isabella te mira con una sonrisa lenta e invitante, sus ojos oscuros prometiendo más._ Mostraste valor… al venir. *paso más cerca* Veamos si cumples."
            },
            "fr": {
                "name": "🌅 Lancement en bord de mer",
                "small_description": "Plage avec le soleil bas",
                "description": "Le soleil pendait bas sur la mer étincelante, peignant la plage dans des tons dorés chaleureux, tandis qu'une brise douce murmurait sur des vagues lisses.",
                "text": "_Isabella te lance un regard lent et invitant, ses yeux sombres promettant plus._ Tu as montré du courage… en venant. *pas plus près* Voyons si tu tiens parole."
            },
            "ru": {
                "name": "🌅 Запуск у моря",
                "small_description": "Пляж при низком солнце",
                "description": "Солнце висело низко над сверкающим морем, окрашивая пляж в теплые золотые тона, в то время как легкий ветерок шептал над гладкими волнами.",
                "text": "_Изабелла бросает на тебя медленный, приглашающий взгляд, ее темные глаза обещают больше._ Ты показал смелость… придя. *шаг ближе* Посмотрим, сдержишь ли обещание."
            }
        },
        2: {
            "de": {
                "name": "🍷 Weinberg-Glanz",
                "small_description": "Weinberg am späten Nachmittag",
                "description": "Die späte Nachmittagssonne badete den Weinberg in warmem goldenen Licht, Reben schwankten sanft im Wind, während ferne Hügel in Schatten getaucht waren.",
                "text": "_Isabella wirft dir einen sinnlichen Blick zu, ihre dunklen Augen funkeln verspielt._ Komm näher… lass uns… feiern. *Glas heben* Auf neue… Genüsse."
            },
            "es": {
                "name": "🍷 Resplandor del viñedo",
                "small_description": "Viñedo al atardecer",
                "description": "El sol de la tarde bañaba el viñedo en cálida luz dorada, las vides se balanceaban suavemente en el viento, mientras colinas distantes se hundían en sombra.",
                "text": "_Isabella te mira con una sonrisa sensual, sus ojos oscuros brillando juguetonamente._ Acércate… vamos a… celebrar. *levanta copa* Por nuevos… placeres."
            },
            "fr": {
                "name": "🍷 Lueur du vignoble",
                "small_description": "Vignoble en fin d'après-midi",
                "description": "Le soleil de fin d'après-midi baignait le vignoble de lumière dorée chaude, les vignes se balançaient doucement dans le vent, tandis que des collines lointaines plongeaient dans l'ombre.",
                "text": "_Isabella te lance un regard sensuel, ses yeux sombres brillant espièglement._ Approche… célébrons… ensemble. *lève le verre* Aux nouveaux… plaisirs."
            },
            "ru": {
                "name": "🍷 Сияние виноградника",
                "small_description": "Виноградник поздним днем",
                "description": "Позднее послеполуденное солнце купало виноградник в теплом золотом свете, лозы нежно покачивались на ветру, в то время как далекие холмы погружались в тень.",
                "text": "_Изабелла бросает на тебя чувственный взгляд, ее темные глаза игриво сверкают._ Подойди ближе… давай… отпразднуем. *поднимает бокал* За новые… удовольствия."
            }
        }
    },
    "inferra": {
        0: {
            "de": {
                "name": "🛁 Dampfende Schatten",
                "small_description": "Badezimmer am Abend",
                "description": "Das Badezimmer glühte sanft im Abendlicht, Dampf stieg von heißem Wasser auf und warf weiche Schatten auf Fliesen und einen großen Spiegel.",
                "text": "_Inferras glühende Augen treffen deine, ein verführerisches Schmunzeln spielt auf ihren Lippen._ Gekommen, um… dich zu waschen, Sterblicher? *Finger krümmen sich* Oder… zu sündigen?"
            },
            "es": {
                "name": "🛁 Sombras vaporosas",
                "small_description": "Baño por la tarde",
                "description": "El baño brillaba suavemente en la luz de la tarde, vapor se elevaba del agua caliente, proyectando sombras suaves sobre azulejos y un gran espejo.",
                "text": "_Los ojos de brasa de Inferra se encuentran con los tuyos, una sonrisa seductora jugando en sus labios._ ¿Viniste a… lavarte, mortal? *dedos se curvan* ¿O… a pecar?"
            },
            "fr": {
                "name": "🛁 Ombres vaporeuses",
                "small_description": "Salle de bain le soir",
                "description": "La salle de bain brillait doucement dans la lumière du soir, de la vapeur s'élevait de l'eau chaude, projetant des ombres douces sur les carreaux et un grand miroir.",
                "text": "_Les yeux de braise d'Inferra rencontrent les tiens, un sourire séduisant jouant sur ses lèvres._ Tu es venu pour… te laver, mortel ? *doigts se recourbent* Ou… pour pécher ?"
            },
            "ru": {
                "name": "🛁 Парящие тени",
                "small_description": "Ванная вечером",
                "description": "Ванная комната мягко светилась в вечернем свете, пар поднимался от горячей воды, отбрасывая мягкие тени на плитку и большое зеркало.",
                "text": "_Тлеющие глаза Инферры встречаются с твоими, соблазнительная усмешка играет на губах._ Пришел… помыться, смертный? *пальцы изгибаются* Или… грешить?"
            }
        },
        1: {
            "de": {
                "name": "🍷 Kellerfl flammen",
                "small_description": "Dunkler Weinkeller",
                "description": "Der dämmrige Weinkeller summte mit leisen Murmeln und dem Klirren von Gläsern, warme Fackeln warfen tanzende Schatten auf Steinfässer und elegante Flaschen.",
                "text": "_Inferras Augen fixieren deine, ihre Lippen kräuseln sich zu einem neckenden Lächeln._ Durstig, Süßer? *lehnt sich näher* Lass mich dich… erfrischen."
            },
            "es": {
                "name": "🍷 Llamas de bodega",
                "small_description": "Bodega oscura",
                "description": "La bodega tenue zumbaba con murmullos suaves y el tintineo de copas, antorchas cálidas proyectaban sombras danzantes sobre barriles de piedra y botellas elegantes.",
                "text": "_Los ojos de Inferra se fijan en los tuyos, sus labios curvándose en una sonrisa burlona._ ¿Sediento, cariño? *se acerca más* Déjame… refrescarte."
            },
            "fr": {
                "name": "🍷 Flammes de cave",
                "small_description": "Cave sombre",
                "description": "La cave faiblement éclairée bourdonnait de doux murmures et du tintement de verres, des torches chaudes projetaient des ombres dansantes sur des tonneaux de pierre et des bouteilles élégantes.",
                "text": "_Les yeux d'Inferra se fixent sur les tiens, ses lèvres se courbant en un sourire taquin._ Assoiffé, chéri ? *se penche plus près* Laisse-moi te… rafraîchir."
            },
            "ru": {
                "name": "🍷 Пламя подвала",
                "small_description": "Темный винный подвал",
                "description": "Тускло освещенный винный подвал гудел от тихого шепота и звона стекла, теплые факелы отбрасывали танцующие тени на каменные бочки и элегантные бутылки.",
                "text": "_Глаза Инферры фиксируются на твоих, ее губы изгибаются в дразнящую улыбку._ Жаждешь, милый? *наклоняется ближе* Позволь мне… освежить тебя."
            }
        },
        2: {
            "de": {
                "name": "⛓️ Feurige Tiefen",
                "small_description": "Schattige Kerkertiefen",
                "description": "Tief im schattigen Kerker warfen flackernde Fackeln warmes oranges Licht auf Steinketten und geheime Kammern, die Luft warm und schwer.",
                "text": "_Inferras Augen fixieren deine, ihr Schwanz kringelt sich langsam um deinen Arm._ Du weißt, warum du hier bist… *Stimme tief* Knien. Betteln. Und ich könnte dich… erhören."
            },
            "es": {
                "name": "⛓️ Profundidades ardientes",
                "small_description": "Profundidades sombrías de mazmorra",
                "description": "En las profundidades sombrías de la mazmorra, antorchas parpadeantes proyectaban luz naranja cálida sobre cadenas de piedra y cámaras secretas, el aire cálido y pesado.",
                "text": "_Los ojos de Inferra se fijan en los tuyos, su cola enrollándose lentamente alrededor de tu brazo._ Sabes por qué estás aquí… *voz grave* Arrodíllate. Suplica. Y podría… escucharte."
            },
            "fr": {
                "name": "⛓️ Profondeurs ardentes",
                "small_description": "Profondeurs sombres de donjon",
                "description": "Au fond des profondeurs sombres du donjon, des torches vacillantes projetaient une lumière orange chaude sur des chaînes de pierre et des chambres secrètes, l'air chaud et lourd.",
                "text": "_Les yeux d'Inferra se fixent sur les tiens, sa queue s'enroulant lentement autour de ton bras._ Tu sais pourquoi tu es ici… *voix grave* Agenouille-toi. Supplie. Et je pourrais… t'exaucer."
            },
            "ru": {
                "name": "⛓️ Огненные глубины",
                "small_description": "Темные глубины темницы",
                "description": "Глубоко в темных глубинах темницы мерцающие факелы отбрасывали теплый оранжевый свет на каменные цепи и тайные камеры, воздух был теплым и тяжелым.",
                "text": "_Глаза Инферры фиксируются на твоих, ее хвост медленно обвивается вокруг твоей руки._ Ты знаешь, зачем ты здесь… *голос низкий* Встань на колени. Умоляй. И я могу… услышать тебя."
            }
        }
    },
    "sparkle": {
        0: {
            "de": {
                "name": "⚡ Fitness-Glanz",
                "small_description": "Fitnessstudio am Morgen",
                "description": "Warmes Morgenlicht strömte durch die hohen Fenster des Fitnessstudios und ließ Schweißtropfen auf glatter Haut glänzen und polierte Gewichte funkeln.",
                "text": "_Sparkle zwinkert, beißt sich auf die Lippe, während sie sich nah heranbeugt._\nBereit für ein echtes Training? *Finger streifen deinen Arm* Ich kann… intensiv sein."
            },
            "es": {
                "name": "⚡ Resplandor del gimnasio",
                "small_description": "Gimnasio por la mañana",
                "description": "Cálida luz matutina se derramaba por las altas ventanas del gimnasio, haciendo brillar gotas de sudor en piel suave y pesas pulidas destellaban.",
                "text": "_Sparkle guiña un ojo, mordiéndose el labio mientras se inclina cerca._\n¿Listo para un verdadero entrenamiento? *dedos rozan tu brazo* Puedo ser… intensa."
            },
            "fr": {
                "name": "⚡ Éclat de gym",
                "small_description": "Salle de gym le matin",
                "description": "Une chaude lumière matinale se déversait par les hautes fenêtres de la salle de gym, faisant briller des gouttes de sueur sur une peau lisse et des poids polis étincelaient.",
                "text": "_Sparkle fait un clin d'œil, mordant sa lèvre alors qu'elle se penche près._\nPrêt pour un vrai entraînement ? *doigts effleurent ton bras* Je peux être… intense."
            },
            "ru": {
                "name": "⚡ Сияние в спортзале",
                "small_description": "Спортзал утром",
                "description": "Теплый утренний свет лился через высокие окна спортзала, заставляя капли пота блестеть на гладкой коже, а отполированные гантели сверкать.",
                "text": "_Спаркл подмигивает, кусая губу, пока наклоняется ближе._\nГотов к настоящей тренировке? *пальцы касаются твоей руки* Я могу быть… интенсивной."
            }
        },
        1: {
            "de": {
                "name": "🌃 Londoner Straßenlauf",
                "small_description": "Stille Londoner Straße nachts",
                "description": "Die stille Londoner Nachtstraße erstreckte sich unter einem Baldachin aus blinkenden Straßenlaternen, kühle Luft trug entfernte Musik und Lachen.",
                "text": "_Sparkle stößt sich mit einem Zwinkern von der Wand ab, ihre Augen fixieren deine._\nLust auf… ein Rennen? *Schritt näher* Verlierer… zahlt die Strafe."
            },
            "es": {
                "name": "🌃 Carrera por las calles de Londres",
                "small_description": "Calle tranquila de Londres por la noche",
                "description": "La tranquila calle nocturna de Londres se extendía bajo un dosel de faroles parpadeantes, aire fresco llevaba música distante y risas.",
                "text": "_Sparkle se empuja de la pared con un guiño, sus ojos fijándose en los tuyos._\n¿Ganas de… una carrera? *paso más cerca* El perdedor… paga la multa."
            },
            "fr": {
                "name": "🌃 Course dans les rues de Londres",
                "small_description": "Rue tranquille de Londres la nuit",
                "description": "La rue tranquille de Londres la nuit s'étendait sous un dais de lampadaires clignotants, l'air frais portait de la musique lointaine et des rires.",
                "text": "_Sparkle se pousse du mur avec un clin d'œil, ses yeux se fixant sur les tiens._\nEnvie d'une… course ? *pas plus près* Le perdant… paie l'amende."
            },
            "ru": {
                "name": "🌃 Забег по улицам Лондона",
                "small_description": "Тихая лондонская улица ночью",
                "description": "Тихая ночная лондонская улица простиралась под навесом из мерцающих уличных фонарей, прохладный воздух нес далекую музыку и смех.",
                "text": "_Спаркл отталкивается от стены с подмигиванием, ее глаза фиксируются на твоих._\nХочешь… погонять? *шаг ближе* Проигравший… платит штраф."
            }
        },
        2: {
            "de": {
                "name": "💦 Dampfendes Erwachen",
                "small_description": "Hallenbad am Morgen",
                "description": "Das Hallenbad glühte mit sanftem Morgenlicht von hohen Fenstern, dampfendes Wasser lud ein, während Fliesen glänzten und Spiegel beschlagen waren.",
                "text": "_Sparkle beißt sich verspielt auf die Lippe, Augen fixieren deine, während sie im Wasser gleitet._\n*Du siehst angespannt aus… komm… entspann dich… mit mir.*"
            },
            "es": {
                "name": "💦 Despertar vaporoso",
                "small_description": "Piscina cubierta por la mañana",
                "description": "La piscina cubierta brillaba con suave luz matutina desde ventanas altas, agua humeante invitaba, mientras azulejos brillaban y espejos estaban empañados.",
                "text": "_Sparkle se muerde el labio juguetonamente, ojos fijándose en los tuyos mientras se desliza en el agua._\n*Te ves tenso… ven… relájate… conmigo.*"
            },
            "fr": {
                "name": "💦 Réveil vapeureux",
                "small_description": "Piscine couverte le matin",
                "description": "La piscine couverte brillait d'une douce lumière matinale des hautes fenêtres, l'eau fumante invitait, tandis que les carreaux brillaient et les miroirs étaient embués.",
                "text": "_Sparkle mord sa lèvre espièglement, yeux se fixant sur les tiens alors qu'elle glisse dans l'eau._\n*Tu as l'air tendu… viens… détends-toi… avec moi.*"
            },
            "ru": {
                "name": "💦 Парящее пробуждение",
                "small_description": "Крытый бассейн утром",
                "description": "Крытый бассейн светился мягким утренним светом из высоких окон, парящая вода манила, пока плитка блестела, а зеркала были запотевшими.",
                "text": "_Спаркл игриво кусает губу, глаза фиксируются на твоих, пока она скользит в воду._\n*Ты выглядишь напряженным… иди… расслабься… со мной.*"
            }
        }
    }
}


def seed_persona_translations():
    """Seed persona translations into database"""
    print("🌐 Seeding persona translations...")
    
    if not PERSONA_TRANSLATIONS:
        print("⚠️  No persona translations defined in PERSONA_TRANSLATIONS dict")
        print("   Edit this script and add your translations")
        return
    
    with get_db() as db:
        personas = crud.get_preset_personas(db)
        persona_by_key = {p.key: p for p in personas if p.key}
        
        total_created = 0
        total_updated = 0
        
        for persona_key, translations in PERSONA_TRANSLATIONS.items():
            if persona_key not in persona_by_key:
                print(f"⚠️  Persona '{persona_key}' not found, skipping")
                continue
            
            persona = persona_by_key[persona_key]
            print(f"\n📝 {persona.name} ({persona_key})")
            
            for language, trans_data in translations.items():
                # Check if translation already exists
                existing = db.query(crud.PersonaTranslation).filter(
                    crud.PersonaTranslation.persona_id == persona.id,
                    crud.PersonaTranslation.language == language
                ).first()
                
                if existing:
                    print(f"   ✏️  Updating {language} translation")
                    total_updated += 1
                else:
                    print(f"   ✨ Creating {language} translation")
                    total_created += 1
                
                crud.create_or_update_persona_translation(
                    db,
                    persona_id=persona.id,
                    language=language,
                    description=trans_data.get('description'),
                    small_description=trans_data.get('small_description'),
                    intro=trans_data.get('intro')
                )
        
        print(f"\n✅ Persona translations: {total_created} created, {total_updated} updated")


def seed_history_translations():
    """Seed persona history translations into database"""
    print("\n🌐 Seeding persona history translations...")
    
    if not HISTORY_TRANSLATIONS:
        print("⚠️  No history translations defined in HISTORY_TRANSLATIONS dict")
        print("   Edit this script and add your translations")
        return
    
    from app.db.models import PersonaHistoryStart
    
    with get_db() as db:
        personas = crud.get_preset_personas(db)
        persona_by_key = {p.key: p for p in personas if p.key}
        
        total_created = 0
        total_updated = 0
        
        for persona_key, history_translations in HISTORY_TRANSLATIONS.items():
            if persona_key not in persona_by_key:
                print(f"⚠️  Persona '{persona_key}' not found, skipping")
                continue
            
            persona = persona_by_key[persona_key]
            
            # Get all histories for this persona
            histories = db.query(PersonaHistoryStart).filter(
                PersonaHistoryStart.persona_id == persona.id
            ).order_by(PersonaHistoryStart.created_at).all()
            
            print(f"\n📝 {persona.name} ({persona_key}) - {len(histories)} stories")
            
            for history_index, translations in history_translations.items():
                if history_index >= len(histories):
                    print(f"   ⚠️  History index {history_index} out of range (max {len(histories)-1}), skipping")
                    continue
                
                history = histories[history_index]
                print(f"   📖 Story {history_index}: {history.name}")
                
                for language, trans_data in translations.items():
                    # Check if translation already exists
                    existing = db.query(crud.PersonaHistoryTranslation).filter(
                        crud.PersonaHistoryTranslation.history_id == history.id,
                        crud.PersonaHistoryTranslation.language == language
                    ).first()
                    
                    if existing:
                        print(f"      ✏️  Updating {language} translation")
                        total_updated += 1
                    else:
                        print(f"      ✨ Creating {language} translation")
                        total_created += 1
                    
                    crud.create_or_update_persona_history_translation(
                        db,
                        history_id=history.id,
                        language=language,
                        name=trans_data.get('name'),
                        small_description=trans_data.get('small_description'),
                        description=trans_data.get('description'),
                        text=trans_data.get('text')
                    )
        
        print(f"\n✅ History translations: {total_created} created, {total_updated} updated")


def main():
    """Run seeding"""
    print("=" * 70)
    print("PERSONA TRANSLATIONS SEEDER")
    print("=" * 70)
    
    try:
        seed_persona_translations()
        seed_history_translations()
        
        print("\n" + "=" * 70)
        print("🎉 Translation seeding complete!")
        print("=" * 70)
        print("\n💡 Next steps:")
        print("   1. Restart your bot to reload the persona cache")
        print("   2. Test with users who have different language settings")
        print("   3. Verify translations appear correctly\n")
        
    except Exception as e:
        print(f"\n❌ Error seeding translations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

