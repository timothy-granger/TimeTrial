#include "HintsDialogImpl.h"
#include "ui_HintsDialogImpl.h"

HintsDialogImpl::HintsDialogImpl(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::HintsDialogImpl)
{
    ui->setupUi(this);

    connect( ui->exportGeometry, SIGNAL( clicked() ), SLOT( exportHtml() ) );

}

HintsDialogImpl::~HintsDialogImpl()
{
    delete ui;
}

void HintsDialogImpl::setTitle( QString sTitle )
{
    this->setWindowTitle( sTitle );
}

void HintsDialogImpl::setIcon( QIcon icon )
{
    this->setWindowIcon( icon );
}

void HintsDialogImpl::setFromFile( QString sHintFile )
{
    QStringList paths;

    paths.append( QApplication::applicationDirPath() + "/docs" );

    ui->hintsBrowser->setSearchPaths( paths );

//  qDebug( "Browser Search Path: %s", qPrintable( ui->hintsBrowser->searchPaths().join("\r\n" ) ) );

    ui->hintsBrowser->setSource( QUrl( sHintFile ) );
}

void HintsDialogImpl::setFromHtml( QString html, bool bScroll )
{
    QString     sHtml = html;

    if ( bScroll )
    {
        sHtml += "\n<a name=\"#end\"><font color=white>.</font></a>";
    }

    ui->hintsBrowser->setHtml( sHtml );

    if ( bScroll )
    {
        ui->hintsBrowser->scrollToAnchor( "#end" );
    }
    QApplication::processEvents( QEventLoop::AllEvents );

}

QString HintsDialogImpl::toHtml()
{
    return ui->hintsBrowser->toHtml();
}

void HintsDialogImpl::keyPressEvent( QKeyEvent *event )
{
    if     ( event->key() == Qt::Key_Escape )
    {
        close();
    }
    else if ( event->key() == Qt::Key_S && event->modifiers() == Qt::CTRL )
    {
//      exportHtml();

    }   //   event->key()
}

void HintsDialogImpl::exportHtml( void )
{
    QString     sHintsFile;
    QString     sDateStamp;
    QDateTime   importDate = QDateTime::currentDateTime();

    sDateStamp = importDate.toString( "yyyy.MM.dd.hh.mm.ss" );

    sHintsFile.sprintf( "tt-results_%s", qPrintable( sDateStamp ) );

    QString sFileName = QFileDialog::getSaveFileName( this, "Export Results", "tt-results.html", tr("HTML File(*.html)" ) );

    if ( !sFileName.isEmpty() )
    {
        QFile   outFile( sFileName );

        if( outFile.open(QIODevice::WriteOnly | QIODevice::Text ) )
        {
            QTextStream out (&outFile);

            out << ui->hintsBrowser->toHtml();

        }

    }   //  if(!sFileName.isEmpty())

}
